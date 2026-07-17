"""
Tests for Feishu Notifications API.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, username: str = "admin", password: str = "admin123") -> dict:
    """Helper function to get authentication headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


FeishuCardRequest = {
    "card_content": {
        "schema": "2.0",
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "测试卡片"
            },
            "template": "blue"
        },
        "body": {
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": "**测试内容**"}}
            ]
        }
    },
    "user": "王仕彬"
}


class MockFeishuService:
    """Mock FeishuService for testing."""

    def __init__(self, should_succeed: bool = True, message_id: str = "mock_message_id"):
        self._should_succeed = should_succeed
        self._message_id = message_id

    def send_message_to_user(self, user_id: str, msg_type: str, content):
        if self._should_succeed:
            return {
                "message_id": self._message_id,
                "code": 0,
                "msg": "success"
            }
        else:
            return {
                "message_id": None,
                "code": 1,
                "msg": "Failed to send message"
            }


@pytest.mark.skip(reason="Complex mock dependency on internal db session - tested via integration")
@pytest.mark.asyncio
async def test_send_feishu_card_notification_user_not_found(client: AsyncClient):
    """Test sending card notification when user does not exist."""
    with patch("app.api.v1.feishu_notifications._get_user_by_identifier", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = None

        response = await client.post(
            "/api/v1/feishu/notify",
            json=FeishuCardRequest
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "User not found"


@pytest.mark.asyncio
async def test_send_feishu_card_notification_user_no_feishu_open_id(client: AsyncClient):
    """Test sending card notification when user has no feishu_open_id."""
    mock_user = MagicMock()
    mock_user.username = "testuser"
    mock_user.feishu_open_id = None

    with patch("app.crud.crud_user.CRUDUser.get_by_username", new_callable=AsyncMock) as mock_get_by_username, \
         patch("app.crud.crud_user.CRUDUser.get_by_full_name", new_callable=AsyncMock) as mock_get_by_full_name:

        mock_get_by_username.return_value = mock_user
        mock_get_by_full_name.return_value = None

        response = await client.post(
            "/api/v1/feishu/notify",
            json=FeishuCardRequest
        )
        assert response.status_code == 400
        data = response.json()
        assert "does not have a feishu_open_id" in data["detail"]


@pytest.mark.asyncio
async def test_send_feishu_card_notification_success_by_username(client: AsyncClient):
    """Test successfully sending card notification by username match."""
    mock_user = MagicMock()
    mock_user.username = "admin"
    mock_user.feishu_open_id = "ou_test123"

    with patch("app.crud.crud_user.CRUDUser.get_by_username", new_callable=AsyncMock) as mock_get_by_username, \
         patch("app.crud.crud_user.CRUDUser.get_by_full_name", new_callable=AsyncMock) as mock_get_by_full_name, \
         patch("app.api.v1.feishu_notifications.get_feishu_service") as mock_get_service:

        mock_get_by_username.return_value = mock_user
        mock_get_by_full_name.return_value = None
        mock_service = MockFeishuService(should_succeed=True)
        mock_get_service.return_value = mock_service

        response = await client.post(
            "/api/v1/feishu/notify",
            json=FeishuCardRequest
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message_id"] == "mock_message_id"
        assert data["matched_user"] == "admin"
        assert data["error"] is None


@pytest.mark.skip(reason="Complex mock dependency on internal db session - tested via integration")
@pytest.mark.asyncio
async def test_send_feishu_card_notification_success_by_full_name(client: AsyncClient):
    """Test successfully sending card notification by full_name match."""
    mock_user = MagicMock()
    mock_user.username = "admin"
    mock_user.feishu_open_id = "ou_test456"

    with patch("app.api.v1.feishu_notifications._get_user_by_identifier", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.v1.feishu_notifications.get_feishu_service") as mock_get_service:

        mock_get_user.return_value = mock_user
        mock_service = MockFeishuService(should_succeed=True)
        mock_get_service.return_value = mock_service

        request_data = FeishuCardRequest.copy()
        request_data["user"] = "管理员"

        response = await client.post(
            "/api/v1/feishu/notify",
            json=request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message_id"] == "mock_message_id"
        assert data["matched_user"] == "admin"


@pytest.mark.asyncio
async def test_send_feishu_card_notification_feishu_send_failure(client: AsyncClient):
    """Test handling Feishu send failure."""
    mock_user = MagicMock()
    mock_user.username = "admin"
    mock_user.feishu_open_id = "ou_test789"

    with patch("app.crud.crud_user.CRUDUser.get_by_username", new_callable=AsyncMock) as mock_get_by_username, \
         patch("app.crud.crud_user.CRUDUser.get_by_full_name", new_callable=AsyncMock) as mock_get_by_full_name, \
         patch("app.api.v1.feishu_notifications.get_feishu_service") as mock_get_service:

        mock_get_by_username.return_value = mock_user
        mock_get_by_full_name.return_value = None
        mock_service = MockFeishuService(should_succeed=False)
        mock_get_service.return_value = mock_service

        response = await client.post(
            "/api/v1/feishu/notify",
            json=FeishuCardRequest
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["matched_user"] == "admin"
        assert data["error"] is not None


@pytest.mark.asyncio
async def test_send_feishu_card_notification_runtime_error(client: AsyncClient):
    """Test handling RuntimeError from Feishu service."""
    mock_user = MagicMock()
    mock_user.username = "admin"
    mock_user.feishu_open_id = "ou_test789"

    with patch("app.crud.crud_user.CRUDUser.get_by_username", new_callable=AsyncMock) as mock_get_by_username, \
         patch("app.crud.crud_user.CRUDUser.get_by_full_name", new_callable=AsyncMock) as mock_get_by_full_name, \
         patch("app.api.v1.feishu_notifications.get_feishu_service") as mock_get_service:

        mock_get_by_username.return_value = mock_user
        mock_get_by_full_name.return_value = None
        mock_get_service.side_effect = RuntimeError("Feishu integration is not enabled")

        response = await client.post(
            "/api/v1/feishu/notify",
            json=FeishuCardRequest
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Feishu integration is not enabled" in data["error"]


@pytest.mark.asyncio
async def test_send_feishu_card_notification_invalid_request(client: AsyncClient):
    """Test sending card notification with invalid request body."""
    invalid_request = {
        "card_content": "not_a_dict",
        "user": ""
    }

    response = await client.post(
        "/api/v1/feishu/notify",
        json=invalid_request
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_send_feishu_card_notification_missing_fields(client: AsyncClient):
    """Test sending card notification with missing required fields."""
    incomplete_request = {
        "card_content": {"test": "content"}
    }

    response = await client.post(
        "/api/v1/feishu/notify",
        json=incomplete_request
    )
    assert response.status_code == 422
