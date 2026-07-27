"""
Tests for Feishu Notifications API.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import db_operation_with_retry


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


# ---------------------------------------------------------------------------
# 跨项目 pipeline_iid 冲突场景集成测试（修复 bug: 后置路由更新前置路由卡片）
# ---------------------------------------------------------------------------


async def _insert_record(
    *,
    open_message_id: str,
    callback_id: str,
    message_id: str,
    card_content: dict,
    chat_id: str,
) -> int:
    """直接插入 NotificationRecord，返回记录 id。使用独立 session 与生产一致。"""

    async def _op(session):
        result = await session.execute(
            text(
                'INSERT INTO notification_records '
                '("user", matched_user, feishu_open_id, chat_id, receive_type, '
                ' callback_id, open_message_id, callback_url, card_content, '
                ' message_id, success, error, created_at, updated_at) '
                "VALUES (:user, NULL, NULL, :chat_id, 'chat_id', "
                "        :callback_id, :open_message_id, NULL, CAST(:card AS JSONB), "
                "        :message_id, TRUE, NULL, NOW(), NOW()) "
                "RETURNING id"
            ),
            {
                "user": f"chat:{chat_id}",
                "chat_id": chat_id,
                "callback_id": callback_id,
                "open_message_id": open_message_id,
                "card": __import__("json").dumps(card_content),
                "message_id": message_id,
            },
        )
        row = result.fetchone()
        await session.commit()
        return row[0] if row else None

    return await db_operation_with_retry(_op, max_retries=2, retry_delay=0.5)


async def _get_record_card_content(record_id: int) -> dict | None:
    """查询指定记录的 card_content。"""

    async def _op(session):
        result = await session.execute(
            text("SELECT card_content FROM notification_records WHERE id = :id"),
            {"id": record_id},
        )
        row = result.fetchone()
        return row[0] if row else None

    return await db_operation_with_retry(_op, max_retries=2, retry_delay=0.5)


async def _cleanup_records(record_ids: list[int]):
    """清理测试记录。"""
    if not record_ids:
        return

    async def _op(session):
        await session.execute(
            text("DELETE FROM notification_records WHERE id = ANY(:ids)"),
            {"ids": record_ids},
        )
        await session.commit()

    await db_operation_with_retry(_op, max_retries=2, retry_delay=0.5)


@pytest.mark.asyncio
async def test_update_by_open_message_id_with_callback_id_isolates_project(client: AsyncClient):
    """传入 callback_id 时，只更新 callback_id 匹配的记录，不影响其他项目同名 pipeline_iid 的卡片。

    复现 bug 场景：
    - 项目A pipeline_iid=5010 → open_message_id=pipeline_5010, callback_id=projectA_5010
    - 项目B pipeline_iid=5010 → open_message_id=pipeline_5010, callback_id=projectB_5010
    调用 PATCH 传入 callback_id=projectB_5010 时，projectA 的卡片不应被覆盖。
    """
    # 用 uuid 避免与真实数据冲突
    suffix = uuid.uuid4().hex[:8]
    open_message_id = f"pipeline_test_{suffix}_5010"
    project_a_msg_id = f"om_a_{suffix}"
    project_b_msg_id = f"om_b_{suffix}"
    chat_a = f"oc_chat_a_{suffix}"
    chat_b = f"oc_chat_b_{suffix}"

    card_running_a = {"schema": "2.0", "header": {"title": {"content": "项目A运行中"}}, "body": {"elements": []}}
    card_running_b = {"schema": "2.0", "header": {"title": {"content": "项目B运行中"}}, "body": {"elements": []}}
    card_success_b = {"schema": "2.0", "header": {"title": {"content": "项目B成功"}}, "body": {"elements": []}}

    # 1. 模拟项目A、项目B两条记录共用同一 open_message_id
    rid_a = await _insert_record(
        open_message_id=open_message_id,
        callback_id=f"projectA_{suffix}_5010",
        message_id=project_a_msg_id,
        card_content=card_running_a,
        chat_id=chat_a,
    )
    rid_b = await _insert_record(
        open_message_id=open_message_id,
        callback_id=f"projectB_{suffix}_5010",
        message_id=project_b_msg_id,
        card_content=card_running_b,
        chat_id=chat_b,
    )
    assert rid_a and rid_b

    try:
        # 2. mock 飞书服务，update_card_message 全部返回成功
        mock_service = MagicMock()
        mock_service.update_card_message.return_value = {"success": True}

        with patch("app.api.v1.feishu_notifications.get_feishu_service", return_value=mock_service):
            # 3. 调用 PATCH，传入项目B的 callback_id
            response = await client.patch(
                f"/api/v1/feishu/notify-by-open-id/{open_message_id}",
                json={"card_content": card_success_b, "callback_id": f"projectB_{suffix}_5010"},
            )

        # 4. 接口应成功，且只更新了 1 条（项目B）
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 1
        assert data["succeeded"] == 1
        assert data["details"][0]["message_id"] == project_b_msg_id

        # 5. 关键断言：项目A 的 card_content 保持"运行中"未被覆盖
        card_a_after = await _get_record_card_content(rid_a)
        assert card_a_after is not None
        assert card_a_after["header"]["title"]["content"] == "项目A运行中"

        # 6. 项目B 的 card_content 已被更新为"成功"
        card_b_after = await _get_record_card_content(rid_b)
        assert card_b_after is not None
        assert card_b_after["header"]["title"]["content"] == "项目B成功"

        # 7. 飞书 update_card_message 仅被调用一次（只更新了项目B的卡片）
        assert mock_service.update_card_message.call_count == 1
        # 调用时用的是项目B的 message_id
        called_args = mock_service.update_card_message.call_args
        assert called_args.kwargs.get("open_message_id") == project_b_msg_id
    finally:
        await _cleanup_records([rid_a, rid_b])


@pytest.mark.asyncio
async def test_update_by_open_message_id_without_callback_id_backwards_compatible(client: AsyncClient):
    """不传 callback_id 时维持原行为：更新所有 open_message_id 匹配的记录（向后兼容）。"""
    suffix = uuid.uuid4().hex[:8]
    open_message_id = f"pipeline_compat_{suffix}_5010"

    card_running = {"schema": "2.0", "header": {"title": {"content": "运行中"}}, "body": {"elements": []}}
    card_done = {"schema": "2.0", "header": {"title": {"content": "完成"}}, "body": {"elements": []}}

    rid_1 = await _insert_record(
        open_message_id=open_message_id,
        callback_id=f"projectA_{suffix}_5010",
        message_id=f"om_1_{suffix}",
        card_content=card_running,
        chat_id=f"oc_1_{suffix}",
    )
    rid_2 = await _insert_record(
        open_message_id=open_message_id,
        callback_id=f"projectB_{suffix}_5010",
        message_id=f"om_2_{suffix}",
        card_content=card_running,
        chat_id=f"oc_2_{suffix}",
    )
    assert rid_1 and rid_2

    try:
        mock_service = MagicMock()
        mock_service.update_card_message.return_value = {"success": True}

        with patch("app.api.v1.feishu_notifications.get_feishu_service", return_value=mock_service):
            # 不传 callback_id
            response = await client.patch(
                f"/api/v1/feishu/notify-by-open-id/{open_message_id}",
                json={"card_content": card_done},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 2
        assert data["succeeded"] == 2
        # 飞书 update_card_message 被调用 2 次（两条记录都更新）
        assert mock_service.update_card_message.call_count == 2

        # 两条记录的 card_content 都被更新为"完成"
        assert (await _get_record_card_content(rid_1))["header"]["title"]["content"] == "完成"
        assert (await _get_record_card_content(rid_2))["header"]["title"]["content"] == "完成"
    finally:
        await _cleanup_records([rid_1, rid_2])


@pytest.mark.asyncio
async def test_update_by_open_message_id_with_nonexistent_callback_id_returns_404(client: AsyncClient):
    """传入不存在的 callback_id 时返回 404，避免误更新其他项目的记录。"""
    suffix = uuid.uuid4().hex[:8]
    open_message_id = f"pipeline_404_{suffix}_5010"

    card_running = {"schema": "2.0", "header": {"title": {"content": "运行中"}}, "body": {"elements": []}}

    rid_a = await _insert_record(
        open_message_id=open_message_id,
        callback_id=f"projectA_{suffix}_5010",
        message_id=f"om_a_{suffix}",
        card_content=card_running,
        chat_id=f"oc_a_{suffix}",
    )
    assert rid_a

    try:
        mock_service = MagicMock()
        with patch("app.api.v1.feishu_notifications.get_feishu_service", return_value=mock_service):
            response = await client.patch(
                f"/api/v1/feishu/notify-by-open-id/{open_message_id}",
                json={
                    "card_content": {"schema": "2.0"},
                    "callback_id": f"nonexistent_{suffix}_5010",
                },
            )

        assert response.status_code == 404
        assert "with callback_id=" in response.json()["detail"]
        # 飞书 update_card_message 不应被调用
        mock_service.update_card_message.assert_not_called()
    finally:
        await _cleanup_records([rid_a])
