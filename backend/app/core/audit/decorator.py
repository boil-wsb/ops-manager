"""
Audit log decorator for automatically logging FastAPI route operations.
"""
import functools
import inspect
import time
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import Request

from app.core.audit.logger import get_audit_logger

F = TypeVar("F", bound=Callable[..., Any])


def audit_log(
    operation_type: str,
    module: str,
    object_type: str | None = None,
    record_before_after: bool = True,
    description: str | None = None,
) -> Callable[[F], F]:
    """
    Decorator for automatically logging FastAPI route operations to audit log.

    Args:
        operation_type: Type of operation (CREATE, UPDATE, DELETE, EXPORT, etc.)
        module: Module name (asset, user, role, etc.)
        object_type: Type of object being operated on (optional)
        record_before_after: Whether to record data before and after operation (default: True)
        description: Optional description of the operation

    Usage:
        @router.post("/assets")
        @audit_log(operation_type="CREATE", module="asset", object_type="Asset")
        async def create_asset(request: Request, ...):
            ...

        @router.put("/assets/{asset_id}")
        @audit_log(operation_type="UPDATE", module="asset", object_type="Asset")
        async def update_asset(request: Request, asset_id: int, ...):
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _execute_with_audit(
                func=func,
                operation_type=operation_type,
                module=module,
                object_type=object_type,
                record_before_after=record_before_after,
                description=description,
                args=args,
                kwargs=kwargs,
            )

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return _execute_with_audit_sync(
                func=func,
                operation_type=operation_type,
                module=module,
                object_type=object_type,
                record_before_after=record_before_after,
                description=description,
                args=args,
                kwargs=kwargs,
            )

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


async def _execute_with_audit(
    func: Callable[..., Any],
    operation_type: str,
    module: str,
    object_type: str | None,
    record_before_after: bool,
    description: str | None,
    args: tuple,
    kwargs: dict,
) -> Any:
    """
    Execute an async function with audit logging.
    """
    audit_logger = get_audit_logger()
    request_id = str(uuid.uuid4())

    # Extract request and other context
    request = _extract_request(args, kwargs)
    operator_info = _extract_operator_info(request, kwargs)

    # Capture before data if needed
    before_data = None
    if record_before_after and operation_type in ("UPDATE", "DELETE"):
        before_data = await _capture_before_data(func, args, kwargs)

    # Record start time
    start_time = time.time()
    error_message = None
    status = "SUCCESS"
    result = None

    try:
        # Execute the actual function
        result = await func(*args, **kwargs)
        return result
    except Exception as e:
        status = "FAILURE"
        error_message = str(e)
        raise
    finally:
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Capture after data if needed
        after_data = None
        if record_before_after and status == "SUCCESS":
            after_data = _extract_result_data(result)

        # Extract object info from result or parameters
        object_id, object_name = _extract_object_info(
            result=result,
            kwargs=kwargs,
            object_type=object_type,
        )

        # Log the audit event
        try:
            await audit_logger.log(
                operation_type=operation_type,
                operation_module=module,
                object_type=object_type,
                object_id=object_id,
                object_name=object_name,
                before_data=before_data,
                after_data=after_data,
                operator_id=operator_info.get("operator_id"),
                operator_name=operator_info.get("operator_name"),
                operator_ip=operator_info.get("operator_ip"),
                user_agent=operator_info.get("user_agent"),
                status=status,
                error_message=error_message,
                request_id=request_id,
                duration_ms=duration_ms,
            )
        except Exception as log_error:
            # Don't let audit logging failures affect the main operation
            import logging
            logging.error(f"Failed to write audit log: {log_error}")


def _execute_with_audit_sync(
    func: Callable[..., Any],
    operation_type: str,
    module: str,
    object_type: str | None,
    record_before_after: bool,
    description: str | None,
    args: tuple,
    kwargs: dict,
) -> Any:
    """
    Execute a sync function with audit logging.
    Note: For sync functions, we use a simplified approach without async database logging.
    """
    audit_logger = get_audit_logger()
    request_id = str(uuid.uuid4())

    # Extract request and other context
    request = _extract_request(args, kwargs)
    operator_info = _extract_operator_info(request, kwargs)

    # Record start time
    start_time = time.time()
    error_message = None
    status = "SUCCESS"
    result = None

    try:
        # Execute the actual function
        result = func(*args, **kwargs)
        return result
    except Exception as e:
        status = "FAILURE"
        error_message = str(e)
        raise
    finally:
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # For sync functions, we only log to file (not database) to avoid async issues
        # The file logging is synchronous
        if audit_logger._file_logger:
            import json

            # Extract object info from result or parameters
            object_id, object_name = _extract_object_info(
                result=result,
                kwargs=kwargs,
                object_type=object_type,
            )

            log_data = {
                'request_id': request_id,
                'type': operation_type,
                'module': module,
                'object': f"{object_type}:{object_id}" if object_type and object_id else None,
                'object_name': object_name,
                'operator': operator_info.get("operator_name") or f"user:{operator_info.get('operator_id')}",
                'ip': operator_info.get("operator_ip"),
                'status': status,
                'duration_ms': duration_ms,
                'error': error_message,
            }

            audit_logger._file_logger.info(
                json.dumps(log_data, ensure_ascii=False, default=str)
            )


def _extract_request(args: tuple, kwargs: dict) -> Request | None:
    """
    Extract FastAPI Request object from function arguments.
    """
    # Check in args
    for arg in args:
        if isinstance(arg, Request):
            return arg

    # Check in kwargs
    for value in kwargs.values():
        if isinstance(value, Request):
            return value

    return None


def _extract_operator_info(request: Request | None, kwargs: dict = None) -> dict[str, Any]:
    """
    Extract operator information from request and kwargs.
    """
    info = {
        "operator_id": None,
        "operator_name": None,
        "operator_ip": None,
        "user_agent": None,
    }

    if request is not None:
        # Extract IP address
        if hasattr(request, 'client') and request.client:
            info["operator_ip"] = request.client.host

        # Try to get forwarded IP if behind proxy
        if hasattr(request, 'headers'):
            forwarded_for = request.headers.get('x-forwarded-for')
            if forwarded_for:
                info["operator_ip"] = forwarded_for.split(',')[0].strip()
            elif not info["operator_ip"]:
                info["operator_ip"] = request.headers.get('x-real-ip')

            # Get user agent
            info["user_agent"] = request.headers.get('user-agent')

        # Extract user info from request state (set by auth middleware)
        if hasattr(request, 'state'):
            state = request.state
            if hasattr(state, 'user'):
                user = state.user
                if isinstance(user, dict):
                    info["operator_id"] = user.get('id')
                    info["operator_name"] = user.get('username') or user.get('name')
                else:
                    info["operator_id"] = getattr(user, 'id', None)
                    info["operator_name"] = getattr(user, 'username', None) or getattr(user, 'name', None)

    # Try to extract username from credentials for login operations
    if kwargs and not info["operator_name"]:
        credentials = kwargs.get('credentials') or kwargs.get('user_login') or kwargs.get('login_data')
        if credentials and hasattr(credentials, 'username'):
            info["operator_name"] = credentials.username
        elif credentials and isinstance(credentials, dict):
            info["operator_name"] = credentials.get('username') or credentials.get('email')

    return info


async def _capture_before_data(
    func: Callable,
    args: tuple,
    kwargs: dict,
) -> dict[str, Any] | None:
    """
    Capture data before operation for UPDATE/DELETE operations.
    This attempts to fetch the existing object data.
    """
    # Try to extract object ID from kwargs
    object_id = kwargs.get('asset_id') or kwargs.get('id') or kwargs.get('object_id')

    if not object_id:
        return None

    # Try to get db session from kwargs
    db = kwargs.get('db') or kwargs.get('session')

    if db is None:
        return None

    try:
        # Try to infer the model class from the function
        # This is a best-effort approach
        func_module = inspect.getmodule(func)
        if func_module and hasattr(func_module, 'crud'):
            crud_obj = getattr(func_module, 'crud', None)
            if crud_obj and hasattr(crud_obj, 'get'):
                existing_obj = await crud_obj.get(db, id=object_id)
                if existing_obj:
                    return _object_to_dict(existing_obj)
    except Exception:
        pass

    return None


def _extract_result_data(result: Any) -> dict[str, Any] | None:
    """
    Extract data from function result for audit logging.
    """
    if result is None:
        return None

    # Handle different response types
    if isinstance(result, dict):
        # If it's a dict response, extract the data
        if 'data' in result:
            return _serialize_dict(_object_to_dict(result['data']))
        return _serialize_dict(result)

    # Handle Pydantic models and SQLAlchemy objects
    return _serialize_dict(_object_to_dict(result))


def _serialize_dict(data: Any) -> Any:
    """Recursively serialize a dict to ensure all values are JSON-compatible."""
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: _serialize_dict(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [_serialize_dict(item) for item in data]
    return _serialize_value(data)


def _extract_object_info(
    result: Any,
    kwargs: dict,
    object_type: str | None,
) -> tuple[str | None, str | None]:
    """
    Extract object ID and name from result or kwargs.
    """
    object_id = None
    object_name = None

    # Try to get from kwargs first
    for key in ['asset_id', 'id', 'object_id', 'user_id', 'role_id']:
        if key in kwargs:
            object_id = str(kwargs[key])
            break

    # Try to get from result
    if result is not None:
        result_dict = _object_to_dict(result)
        if isinstance(result_dict, dict):
            if not object_id:
                object_id = str(result_dict.get('id', '')) if result_dict.get('id') else None
            object_name = result_dict.get('name') or result_dict.get('username') or result_dict.get('title')

    return object_id, object_name


def _object_to_dict(obj: Any) -> Any:
    """
    Convert an object to a dictionary for audit logging.
    """
    if obj is None:
        return None

    if isinstance(obj, dict):
        return obj

    # Handle Pydantic models (v1 and v2)
    if hasattr(obj, 'model_dump'):
        try:
            return obj.model_dump()
        except Exception:
            pass
    elif hasattr(obj, 'dict'):
        try:
            return obj.dict()
        except Exception:
            pass

    # Handle SQLAlchemy models - use __dict__ to avoid lazy loading issues
    if hasattr(obj, '__table__'):
        try:
            obj_dict = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    obj_dict[key] = _serialize_value(value)
            return obj_dict
        except Exception:
            pass

    # Handle list of objects
    if isinstance(obj, list | tuple):
        return [_object_to_dict(item) for item in obj]

    # Return as-is for primitive types
    return obj


def _serialize_value(value: Any) -> Any:
    """Serialize a value to JSON-compatible format."""
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_serialize_value(item) for item in value]
    return str(value)


def get_current_user_info(request: Request) -> dict[str, Any]:
    """
    Utility function to get current user info from request.
    Can be used outside of the decorator.
    """
    return _extract_operator_info(request)
