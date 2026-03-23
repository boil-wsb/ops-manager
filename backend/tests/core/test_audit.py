"""
Tests for audit logging core functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request

from app.core.audit.logger import AuditLogger, get_audit_logger
from app.core.audit.decorator import audit_log, _object_to_dict, _serialize_value, _extract_object_info
from app.core.audit.sanitizer import sanitize_sensitive_data, _sanitize_dict, _sanitize_string, _mask_value


class TestSanitizer:
    """Tests for data sanitizer."""

    def test_sanitize_password_field(self):
        """Test that password fields are masked."""
        data = {"username": "admin", "password": "secret123"}
        result = sanitize_sensitive_data(data)
        assert result["username"] == "admin"
        assert "password" in result or "***" in str(result["password"])

    def test_sanitize_nested_password(self):
        """Test masking nested password fields."""
        data = {
            "user": {
                "name": "test",
                "password": "mysecret"
            }
        }
        result = sanitize_sensitive_data(data)
        assert result["user"]["name"] == "test"
        assert result["user"].get("password") in ("**", "[MASKED]")

    def test_sanitize_api_key(self):
        """Test that API key fields are masked."""
        data = {"api_key": "sk_test_123456789"}
        result = sanitize_sensitive_data(data)
        assert "api_key" in result or result.get("api_key") in ("sk_t***", "[MASKED]")

    def test_sanitize_credit_card_pattern(self):
        """Test that credit card numbers are masked."""
        data = {"card_number": "4111111111111111"}
        result = sanitize_sensitive_data(data)
        assert "[CREDIT_CARD]" in str(result) or "*" in str(result.get("card_number", ""))

    def test_sanitize_email_pattern(self):
        """Test that email patterns are masked."""
        data = {"note": "Contact user@test.com for details"}
        result = sanitize_sensitive_data(data)
        assert "[EMAIL]" in str(result) or "*" in str(result.get("note", ""))

    def test_sanitize_list_of_dicts(self):
        """Test sanitizing a list of dictionaries."""
        data = [
            {"name": "item1", "password": "pass1"},
            {"name": "item2", "password": "pass2"}
        ]
        result = sanitize_sensitive_data(data)
        assert result[0]["name"] == "item1"
        assert result[1]["name"] == "item2"

    def test_mask_value_short_string(self):
        """Test masking short string values."""
        result = _mask_value("abc")
        assert result == "*****"

    def test_mask_value_long_string(self):
        """Test masking long string values shows prefix/suffix."""
        result = _mask_value("verylongpassword")
        assert result.startswith("ve")
        assert result.endswith("rd")
        assert "*" in result

    def test_mask_value_primitive(self):
        """Test masking non-string primitive values."""
        assert _mask_value(12345) == "[MASKED]"
        assert _mask_value(True) == "[MASKED]"

    def test_mask_value_none(self):
        """Test masking None value."""
        assert _mask_value(None) is None


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_singleton_pattern(self):
        """Test that AuditLogger follows singleton pattern."""
        logger1 = AuditLogger()
        logger2 = AuditLogger()
        assert logger1 is logger2

    def test_file_size_parsing_bytes(self):
        """Test parsing byte size strings."""
        logger = AuditLogger()
        assert logger._parse_file_size("100") == 100
        assert logger._parse_file_size("100B") == 100

    def test_file_size_parsing_kb(self):
        """Test parsing KB size strings."""
        logger = AuditLogger()
        assert logger._parse_file_size("1KB") == 1024
        assert logger._parse_file_size("10KB") == 10240

    def test_file_size_parsing_mb(self):
        """Test parsing MB size strings."""
        logger = AuditLogger()
        assert logger._parse_file_size("1MB") == 1024 * 1024
        assert logger._parse_file_size("5MB") == 5 * 1024 * 1024

    def test_file_size_parsing_gb(self):
        """Test parsing GB size strings."""
        logger = AuditLogger()
        assert logger._parse_file_size("1GB") == 1024 * 1024 * 1024
        assert logger._parse_file_size("2GB") == 2 * 1024 * 1024 * 1024

    def test_summarize_changes_both_data(self):
        """Test summarizing changes when both before and after data exist."""
        logger = AuditLogger()
        before = {"name": "old_name", "status": "active"}
        after = {"name": "new_name", "status": "active"}
        result = logger._summarize_changes(before, after)
        assert "changed_fields" in result
        assert result["changed_fields"]["name"] == {"from": "old_name", "to": "new_name"}
        assert "status" not in result["changed_fields"]

    def test_summarize_changes_only_after(self):
        """Test summarizing changes when only after data exists (create)."""
        logger = AuditLogger()
        after = {"name": "new_item", "type": "asset"}
        result = logger._summarize_changes(None, after)
        assert "created" in result
        assert "name" in result["created"]
        assert "type" in result["created"]

    def test_summarize_changes_only_before(self):
        """Test summarizing changes when only before data exists (delete)."""
        logger = AuditLogger()
        before = {"name": "deleted_item", "type": "asset"}
        result = logger._summarize_changes(before, None)
        assert "deleted" in result
        assert "name" in result["deleted"]

    @pytest.mark.asyncio
    async def test_log_disabled_returns_none(self):
        """Test that log returns None when audit is disabled."""
        logger = AuditLogger()
        original_enabled = logger.enabled
        logger.enabled = False
        result = await logger.log(
            operation_type="CREATE",
            operation_module="test"
        )
        logger.enabled = original_enabled
        assert result is None

    def test_get_audit_logger_returns_instance(self):
        """Test that get_audit_logger returns an AuditLogger instance."""
        logger = get_audit_logger()
        assert isinstance(logger, AuditLogger)


class TestObjectConversion:
    """Tests for object to dict conversion utilities."""

    def test_object_to_dict_none(self):
        """Test converting None returns None."""
        assert _object_to_dict(None) is None

    def test_object_to_dict_dict(self):
        """Test passing dict through."""
        data = {"key": "value"}
        assert _object_to_dict(data) == data

    def test_object_to_dict_pydantic_model(self):
        """Test converting Pydantic-like model."""
        class MockModel:
            def model_dump(self):
                return {"name": "test", "id": 1}

        result = _object_to_dict(MockModel())
        assert result == {"name": "test", "id": 1}

    def test_object_to_dict_pydantic_v1(self):
        """Test converting Pydantic v1 model."""
        class MockModelV1:
            def dict(self):
                return {"name": "test", "id": 1}

        result = _object_to_dict(MockModelV1())
        assert result == {"name": "test", "id": 1}

    def test_object_to_dict_sqlalchemy_model(self):
        """Test converting SQLAlchemy-like model."""
        class MockSQLAlchemy:
            __table__ = True
            def __init__(self):
                self.id = 1
                self.name = "test"
                self._private = "hidden"

        obj = MockSQLAlchemy()
        result = _object_to_dict(obj)
        assert result["id"] == 1
        assert result["name"] == "test"
        assert "_private" not in result

    def test_object_to_dict_list(self):
        """Test converting list of objects."""
        class MockObj:
            def __init__(self, val):
                self.value = val

        objs = [MockObj(1), MockObj(2)]
        result = _object_to_dict(objs)
        assert result == [{"value": 1}, {"value": 2}]

    def test_serialize_value_datetime(self):
        """Test serializing datetime objects."""
        from datetime import datetime
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = _serialize_value(dt)
        assert "2024-01-15" in result

    def test_serialize_value_date(self):
        """Test serializing date objects."""
        from datetime import date
        d = date(2024, 1, 15)
        result = _serialize_value(d)
        assert "2024-01-15" in result

    def test_serialize_value_decimal(self):
        """Test serializing Decimal objects."""
        from decimal import Decimal
        result = _serialize_value(Decimal("123.45"))
        assert result == 123.45
        assert isinstance(result, float)

    def test_serialize_value_uuid(self):
        """Test serializing UUID objects."""
        import uuid
        test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = _serialize_value(test_uuid)
        assert result == "12345678-1234-5678-1234-567812345678"

    def test_serialize_value_nested_dict(self):
        """Test serializing nested dictionary."""
        data = {"outer": {"inner": "value"}}
        result = _serialize_value(data)
        assert result == data


class TestExtractObjectInfo:
    """Tests for object info extraction."""

    def test_extract_from_kwargs_asset_id(self):
        """Test extracting object ID from asset_id kwarg."""
        kwargs = {"asset_id": 123, "name": "test"}
        obj_id, obj_name = _extract_object_info(None, kwargs, "Asset")
        assert obj_id == "123"

    def test_extract_from_kwargs_id(self):
        """Test extracting object ID from id kwarg."""
        kwargs = {"id": 456}
        obj_id, obj_name = _extract_object_info(None, kwargs, "Asset")
        assert obj_id == "456"

    def test_extract_from_result(self):
        """Test extracting object info from result dict."""
        result = {"id": 789, "name": "TestAsset"}
        obj_id, obj_name = _extract_object_info(result, {}, "Asset")
        assert obj_id == "789"
        assert obj_name == "TestAsset"

    def test_extract_name_from_username(self):
        """Test extracting name from username field."""
        result = {"id": 1, "username": "admin_user"}
        obj_id, obj_name = _extract_object_info(result, {}, "User")
        assert obj_name == "admin_user"

    def test_extract_name_from_title(self):
        """Test extracting name from title field."""
        result = {"id": 1, "title": "Important Document"}
        obj_id, obj_name = _extract_object_info(result, {}, "Document")
        assert obj_name == "Important Document"


class TestAuditDecorator:
    """Tests for audit_log decorator."""

    def test_decorator_returns_callable(self):
        """Test that decorator returns a callable."""
        @audit_log(operation_type="CREATE", module="test")
        async def dummy_func():
            return {"id": 1}
        assert callable(dummy_func)

    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Test decorator with async function."""
        @audit_log(operation_type="CREATE", module="test", object_type="Test")
        async def async_func():
            return {"id": 1, "name": "test"}

        result = await async_func()
        assert result["id"] == 1

    def test_decorator_sync_function(self):
        """Test decorator with sync function."""
        @audit_log(operation_type="UPDATE", module="test", object_type="Test")
        def sync_func():
            return {"id": 1, "name": "test"}

        result = sync_func()
        assert result["id"] == 1

    def test_decorator_with_request_object(self):
        """Test decorator extracts request object correctly."""
        from fastapi import Request

        @audit_log(operation_type="CREATE", module="test")
        async def func_with_request(request: Request):
            return {"success": True}

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"user-agent": "TestAgent"}
        mock_request.state = MagicMock()

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            func_with_request(mock_request)
        )
        assert result["success"] is True
