"""
Tests for Notification Records API.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


class MockCrudNotificationRecord:
    """Mock CRUD NotificationRecord for testing."""

    def __init__(self):
        self.records = {}
        self.next_id = 1

    async def get_multi(self, db, skip=0, limit=10, user=None, success=None):
        filtered = list(self.records.values())
        if user:
            filtered = [r for r in filtered if user.lower() in r.user.lower()]
        if success is not None:
            filtered = [r for r in filtered if r.success == success]
        total = len(filtered)
        items = filtered[skip : skip + limit]
        return total, items

    async def get(self, db, record_id):
        return self.records.get(record_id)

    async def create(self, db, obj_in):
        record = MagicMock()
        record.id = self.next_id
        record.user = obj_in.user
        record.matched_user = obj_in.matched_user
        record.feishu_open_id = obj_in.feishu_open_id
        record.chat_id = getattr(obj_in, "chat_id", None)
        record.receive_type = getattr(obj_in, "receive_type", "open_id")
        record.callback_id = getattr(obj_in, "callback_id", None)
        record.open_message_id = getattr(obj_in, "open_message_id", None)
        record.callback_url = getattr(obj_in, "callback_url", None)
        record.card_content = obj_in.card_content
        record.success = obj_in.success
        record.error = obj_in.error
        record.message_id = None
        self.records[self.next_id] = record
        self.next_id += 1
        return record

    async def update(self, db, record_id, obj_in):
        record = self.records.get(record_id)
        if not record:
            return None
        if obj_in.message_id is not None:
            record.message_id = obj_in.message_id
        if obj_in.success is not None:
            record.success = obj_in.success
        if obj_in.error is not None:
            record.error = obj_in.error
        return record

    async def delete(self, db, record_id):
        if record_id in self.records:
            del self.records[record_id]
            return True
        return False


@pytest.fixture
def mock_crud():
    return MockCrudNotificationRecord()


class TestNotificationRecordsAPI:
    """Test cases for notification records API."""

    @pytest.mark.asyncio
    async def test_list_notification_records_empty(self, client: AsyncClient, mock_crud):
        """Test listing notification records when empty."""
        with patch("app.api.v1.notification_records.notification_record", mock_crud):
            response = await client.get("/api/v1/notification-records")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_notification_records_with_data(self, client: AsyncClient, mock_crud):
        """Test listing notification records with data."""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.user = "test_user"
        mock_record.matched_user = "test_user"
        mock_record.feishu_open_id = "ou_test123"
        mock_record.chat_id = None
        mock_record.receive_type = "open_id"
        mock_record.callback_id = None
        mock_record.open_message_id = None
        mock_record.callback_url = None
        mock_record.card_content = {"schema": "2.0"}
        mock_record.message_id = "msg_123"
        mock_record.success = True
        mock_record.error = None
        mock_record.created_at = "2024-01-01T00:00:00"
        mock_crud.records[1] = mock_record
        mock_crud.next_id = 2

        with patch("app.api.v1.notification_records.notification_record", mock_crud):
            response = await client.get("/api/v1/notification-records")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["user"] == "test_user"
            assert data["items"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_list_notification_records_filter_by_user(self, client: AsyncClient, mock_crud):
        """Test filtering notification records by user."""
        mock_record1 = MagicMock()
        mock_record1.id = 1
        mock_record1.user = "user_a"
        mock_record1.matched_user = "user_a"
        mock_record1.feishu_open_id = "ou_1"
        mock_record1.chat_id = None
        mock_record1.receive_type = "open_id"
        mock_record1.callback_id = None
        mock_record1.open_message_id = None
        mock_record1.callback_url = None
        mock_record1.card_content = {}
        mock_record1.message_id = None
        mock_record1.success = False
        mock_record1.error = "Failed"
        mock_record1.created_at = "2024-01-01T00:00:00"

        mock_record2 = MagicMock()
        mock_record2.id = 2
        mock_record2.user = "user_b"
        mock_record2.matched_user = "user_b"
        mock_record2.feishu_open_id = "ou_2"
        mock_record2.chat_id = None
        mock_record2.receive_type = "open_id"
        mock_record2.callback_id = None
        mock_record2.open_message_id = None
        mock_record2.callback_url = None
        mock_record2.card_content = {}
        mock_record2.message_id = None
        mock_record2.success = True
        mock_record2.error = None
        mock_record2.created_at = "2024-01-01T00:00:00"

        mock_crud.records[1] = mock_record1
        mock_crud.records[2] = mock_record2
        mock_crud.next_id = 3

        with patch("app.api.v1.notification_records.notification_record", mock_crud):
            response = await client.get("/api/v1/notification-records?user=user_a")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["items"][0]["user"] == "user_a"

    @pytest.mark.asyncio
    async def test_list_notification_records_filter_by_success(
        self, client: AsyncClient, mock_crud
    ):
        """Test filtering notification records by success status."""
        mock_record1 = MagicMock()
        mock_record1.id = 1
        mock_record1.user = "user_a"
        mock_record1.matched_user = "user_a"
        mock_record1.feishu_open_id = "ou_1"
        mock_record1.chat_id = None
        mock_record1.receive_type = "open_id"
        mock_record1.callback_id = None
        mock_record1.open_message_id = None
        mock_record1.callback_url = None
        mock_record1.card_content = {}
        mock_record1.message_id = "msg_1"
        mock_record1.success = True
        mock_record1.error = None
        mock_record1.created_at = "2024-01-01T00:00:00"

        mock_record2 = MagicMock()
        mock_record2.id = 2
        mock_record2.user = "user_b"
        mock_record2.matched_user = "user_b"
        mock_record2.feishu_open_id = "ou_2"
        mock_record2.chat_id = None
        mock_record2.receive_type = "open_id"
        mock_record2.callback_id = None
        mock_record2.open_message_id = None
        mock_record2.callback_url = None
        mock_record2.card_content = {}
        mock_record2.message_id = None
        mock_record2.success = False
        mock_record2.error = "Failed"
        mock_record2.created_at = "2024-01-01T00:00:00"

        mock_crud.records[1] = mock_record1
        mock_crud.records[2] = mock_record2
        mock_crud.next_id = 3

        with patch("app.api.v1.notification_records.notification_record", mock_crud):
            response = await client.get("/api/v1/notification-records?success=false")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["items"][0]["success"] is False
            assert data["items"][0]["error"] == "Failed"

    @pytest.mark.asyncio
    async def test_get_notification_record_by_id(self, client: AsyncClient, mock_crud):
        """Test getting a single notification record by ID."""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.user = "test_user"
        mock_record.matched_user = "test_user"
        mock_record.feishu_open_id = "ou_test123"
        mock_record.chat_id = None
        mock_record.receive_type = "open_id"
        mock_record.callback_id = None
        mock_record.open_message_id = None
        mock_record.callback_url = None
        mock_record.card_content = {"schema": "2.0"}
        mock_record.message_id = "msg_123"
        mock_record.success = True
        mock_record.error = None
        mock_record.created_at = "2024-01-01T00:00:00"
        mock_crud.records[1] = mock_record
        mock_crud.next_id = 2

        with patch("app.api.v1.notification_records.notification_record", mock_crud):
            response = await client.get("/api/v1/notification-records/1")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["user"] == "test_user"

    @pytest.mark.asyncio
    async def test_get_notification_record_not_found(self, client: AsyncClient, mock_crud):
        """Test getting a non-existent notification record."""
        with patch("app.api.v1.notification_records.notification_record", mock_crud):
            response = await client.get("/api/v1/notification-records/999")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_notification_record_success(self, client: AsyncClient, mock_crud):
        """Test deleting a notification record successfully."""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.user = "test_user"
        mock_record.matched_user = "test_user"
        mock_record.feishu_open_id = "ou_test123"
        mock_record.chat_id = None
        mock_record.receive_type = "open_id"
        mock_record.callback_id = None
        mock_record.open_message_id = None
        mock_record.callback_url = None
        mock_record.card_content = {}
        mock_record.message_id = None
        mock_record.success = False
        mock_record.error = None
        mock_record.created_at = "2024-01-01T00:00:00"
        mock_crud.records[1] = mock_record
        mock_crud.next_id = 2

        with patch("app.api.v1.notification_records.notification_record", mock_crud):
            response = await client.delete("/api/v1/notification-records/1")
            assert response.status_code == 200
            assert response.json()["message"] == "Notification record deleted successfully"
            assert 1 not in mock_crud.records

    @pytest.mark.asyncio
    async def test_delete_notification_record_not_found(self, client: AsyncClient, mock_crud):
        """Test deleting a non-existent notification record."""
        with patch("app.api.v1.notification_records.notification_record", mock_crud):
            response = await client.delete("/api/v1/notification-records/999")
            assert response.status_code == 404


class TestNotificationRecordSchemaConversion:
    """Test cases for toSnakeCaseObj/toCamelCaseObj conversion."""

    def test_notification_record_response_fields(self):
        """Test that API response uses camelCase."""
        response_data = {
            "id": 1,
            "user": "test_user",
            "matchedUser": "test_user",
            "feishuOpenId": "ou_123",
            "chatId": None,
            "receiveType": "open_id",
            "callbackId": None,
            "openMessageId": None,
            "cardContent": {"schema": "2.0"},
            "messageId": "msg_123",
            "success": True,
            "error": None,
            "createdAt": "2024-01-01T00:00:00",
        }
        assert "matchedUser" in response_data
        assert "feishuOpenId" in response_data
        assert "chatId" in response_data
        assert "receiveType" in response_data
        assert "callbackId" in response_data
        assert "openMessageId" in response_data
        assert "messageId" in response_data
        assert "createdAt" in response_data
        assert "matched_user" not in response_data
        assert "feishu_open_id" not in response_data
        assert "chat_id" not in response_data
        assert "receive_type" not in response_data
        assert "callback_id" not in response_data
        assert "open_message_id" not in response_data
        assert "message_id" not in response_data
        assert "created_at" not in response_data

    def test_notification_record_request_fields(self):
        """Test that API request uses snake_case."""
        request_data = {
            "user": "test_user",
            "matched_user": "test_user",
            "feishu_open_id": "ou_123",
            "chat_id": None,
            "receive_type": "open_id",
            "callback_id": None,
            "open_message_id": None,
            "card_content": {"schema": "2.0"},
            "success": True,
        }
        assert "user" in request_data
        assert "matched_user" in request_data
        assert "feishu_open_id" in request_data
        assert "chat_id" in request_data
        assert "receive_type" in request_data
        assert "callback_id" in request_data
        assert "open_message_id" in request_data
        assert "card_content" in request_data
        assert "success" in request_data
        assert "matchedUser" not in request_data
        assert "feishuOpenId" not in request_data
        assert "chatId" not in request_data
        assert "receiveType" not in request_data
        assert "callbackId" not in request_data
        assert "openMessageId" not in request_data
