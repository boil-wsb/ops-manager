"""Auth service API routes for external service role verification.

外部服务（同信任网段）通过工号查询用户角色，确认是否具备行政/采购/营销角色。
信任网段内免 JWT，依赖 auth_middleware 放行配置。
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.audit import audit_log
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.core.security import get_password_hash
from app.crud.crud_user import crud_user

router = APIRouter(prefix="/auth-service", tags=["外部鉴权服务"])
logger = get_logger(__name__)

# 外部鉴权关心的业务角色 code → name 映射
BUSINESS_ROLES: dict[str, str] = {
    "admin_dept": "行政",
    "procurement": "采购",
    "marketing": "营销",
}


class EmployeeRoleVerifyRequest(BaseModel):
    """外部鉴权请求体。"""

    employee_id: str = Field(..., min_length=1, max_length=64, description="工号")


class RoleInfo(BaseModel):
    """角色简要信息。"""

    name: str
    code: str


class EmployeeRoleVerifyResponse(BaseModel):
    """外部鉴权响应体。"""

    employee_id: str
    authorized: bool
    role: str | None = None
    code: str | None = None
    full_name: str | None = None
    matched_roles: list[RoleInfo] = []


class EmployeePasswordResetRequest(BaseModel):
    """外部密码重置请求体。"""

    employee_id: str = Field(..., min_length=1, max_length=64, description="工号")


class EmployeePasswordResetResponse(BaseModel):
    """外部密码重置响应体。"""

    employee_id: str
    full_name: str | None = None
    reset: bool = True
    must_change_password: bool = True


@router.post("/verify-role", response_model=EmployeeRoleVerifyResponse)
@limiter.limit("60/minute")
@audit_log(operation_type="EXTERNAL_ROLE_VERIFY", module="auth")
async def verify_role(
    request: Request,
    body: EmployeeRoleVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """根据工号验证用户角色。

    外部服务携带 employee_id（工号）调用本接口，
    若用户拥有行政/采购/营销任一角色，则返回 authorized=true 及角色信息。
    """
    logger.info(
        "收到外部角色验证请求",
        extra={"action": "auth_service.verify_role", "employee_id": body.employee_id},
    )

    user = await crud_user.get_by_employee_id(db, employee_id=body.employee_id)
    if not user:
        logger.warning(
            f"工号 '{body.employee_id}' 不存在",
            extra={"action": "auth_service.verify_role", "employee_id": body.employee_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工号不存在",
        )

    if not user.is_active:
        logger.warning(
            f"工号 '{body.employee_id}' 对应的用户已停用",
            extra={"action": "auth_service.verify_role", "employee_id": body.employee_id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已停用",
        )

    # 匹配用户启用的角色中命中的业务角色
    matched = [
        {"name": BUSINESS_ROLES[r.code], "code": r.code}
        for r in user.roles
        if r.is_active and r.code in BUSINESS_ROLES
    ]

    if matched:
        # 取第一个匹配的角色作为主角色
        primary = matched[0]
        logger.info(
            f"工号 '{body.employee_id}' 角色验证通过: {primary['code']}",
            extra={
                "action": "auth_service.verify_role",
                "employee_id": body.employee_id,
                "matched": matched,
                "authorized": True,
            },
        )
        return EmployeeRoleVerifyResponse(
            employee_id=body.employee_id,
            authorized=True,
            role=primary["name"],
            code=primary["code"],
            full_name=user.full_name,
            matched_roles=[RoleInfo(**r) for r in matched],
        )

    logger.info(
        f"工号 '{body.employee_id}' 不存在匹配角色",
        extra={
            "action": "auth_service.verify_role",
            "employee_id": body.employee_id,
            "authorized": False,
        },
    )
    return EmployeeRoleVerifyResponse(
        employee_id=body.employee_id,
        authorized=False,
        full_name=user.full_name,
    )


@router.post("/reset-password", response_model=EmployeePasswordResetResponse)
@limiter.limit("10/minute")
@audit_log(operation_type="CHANGE_PASSWORD", module="system")
async def reset_password(
    request: Request,
    body: EmployeePasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """外部密码重置：将工号对应用户的登录密码重置为工号本身，并置强制改密标记。

    信任网段内免 JWT（同 verify-role）。复用改密核心逻辑（与 auth.change-password
    同一密码写入路径 get_password_hash），差异仅两点：密码来源为工号本身（管理员
    重置场景免旧密码校验）、must_change_password 置 True 而非清除。
    """
    logger.info(
        "收到外部密码重置请求",
        extra={"action": "auth_service.reset_password", "employee_id": body.employee_id},
    )

    # 调用方身份验证：共享内部令牌（X-Internal-Token），未配置令牌时一律拒绝（fail-closed），
    # 防止信任网段被放宽或突破后任意账号被批量接管
    expected_token = (settings.auth_service_reset_token or "").strip()
    provided_token = request.headers.get("X-Internal-Token") or ""
    if not expected_token or not secrets.compare_digest(provided_token, expected_token):
        logger.warning(
            "外部密码重置被拒绝（内部令牌缺失或不匹配）",
            extra={"action": "auth_service.reset_password", "employee_id": body.employee_id},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权的重置请求",
        )

    user = await crud_user.get_by_employee_id(db, employee_id=body.employee_id)
    if not user:
        logger.warning(
            f"工号 '{body.employee_id}' 不存在",
            extra={"action": "auth_service.reset_password", "employee_id": body.employee_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工号不存在",
        )

    if not user.is_active:
        logger.warning(
            f"工号 '{body.employee_id}' 对应的用户已停用",
            extra={"action": "auth_service.reset_password", "employee_id": body.employee_id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已停用",
        )

    # 复用改密核心逻辑（与 auth.py change-password 同一密码写入路径）
    user.hashed_password = get_password_hash(user.employee_id)  # 密码重置为工号本身
    user.must_change_password = True                            # 下次登录强制改密
    await db.commit()
    await db.refresh(user)

    logger.info(
        f"工号 '{body.employee_id}' 密码重置成功",
        extra={"action": "auth_service.reset_password", "employee_id": body.employee_id},
    )
    return EmployeePasswordResetResponse(
        employee_id=user.employee_id,
        full_name=user.full_name,
    )
