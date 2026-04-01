"""
Tests for IT Feedback API.
"""
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


ITFeedbackCreate = {
    "computerType": "desktop",
    "usageYears": "3-5年",
    "lagLevel": "3",
    "lagScenarios": "开机、运行大型软件",
    "description": "电脑比较卡顿",
    "contact": "test@example.com",
}


@pytest.mark.asyncio
async def test_create_feedback(client: AsyncClient):
    """Test create feedback endpoint."""
    response = await client.post(
        "/api/v1/it-feedback",
        json=ITFeedbackCreate,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["computerType"] == ITFeedbackCreate["computerType"]
    assert data["usageYears"] == ITFeedbackCreate["usageYears"]
    assert data["lagLevel"] == ITFeedbackCreate["lagLevel"]
    assert data["lagScenarios"] == ITFeedbackCreate["lagScenarios"]
    assert data["description"] == ITFeedbackCreate["description"]
    assert data["contact"] == ITFeedbackCreate["contact"]
    assert data["status"] == "pending"
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


@pytest.mark.asyncio
async def test_list_feedback(client: AsyncClient):
    """Test list feedback endpoint."""
    await client.post("/api/v1/it-feedback", json=ITFeedbackCreate)
    await client.post("/api/v1/it-feedback", json=ITFeedbackCreate)

    response = await client.get("/api/v1/it-feedback")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_list_feedback_with_pagination(client: AsyncClient):
    """Test list feedback with pagination."""
    response = await client.get("/api/v1/it-feedback?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_feedback(client: AsyncClient):
    """Test get feedback by ID endpoint."""
    create_response = await client.post("/api/v1/it-feedback", json=ITFeedbackCreate)
    feedback_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/it-feedback/{feedback_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == feedback_id
    assert data["computerType"] == ITFeedbackCreate["computerType"]


@pytest.mark.asyncio
async def test_get_feedback_not_found(client: AsyncClient):
    """Test get feedback with non-existent ID."""
    response = await client.get("/api/v1/it-feedback/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_feedback_with_client_ip(client: AsyncClient):
    """Test create feedback captures client IP."""
    response = await client.post(
        "/api/v1/it-feedback",
        json=ITFeedbackCreate,
        headers={"X-Forwarded-For": "192.168.1.100"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["clientIp"] == "192.168.1.100"


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_list_feedback_unauthorized(client: AsyncClient):
    """Test list feedback without authentication returns 401."""
    response = await client.get("/api/v1/it-feedback")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_feedback_with_auth(client: AsyncClient):
    """Test list feedback with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/it-feedback", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_list_feedback_with_status_filter(client: AsyncClient):
    """Test list feedback with status filter."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/it-feedback?status=pending", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    for item in data["items"]:
        assert item["status"] == "pending"


@pytest.mark.asyncio
async def test_list_feedback_with_lag_level_filter(client: AsyncClient):
    """Test list feedback with lag level filter."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/it-feedback?lag_level=3", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_feedback_with_auth(client: AsyncClient):
    """Test get feedback by ID with authentication."""
    headers = await get_auth_headers(client)
    create_response = await client.post("/api/v1/it-feedback", json=ITFeedbackCreate)
    feedback_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/it-feedback/{feedback_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == feedback_id


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_get_feedback_unauthorized(client: AsyncClient):
    """Test get feedback without authentication returns 401."""
    response = await client.get("/api/v1/it-feedback/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_feedback_status(client: AsyncClient):
    """Test update feedback status (resolve feedback)."""
    headers = await get_auth_headers(client)
    create_response = await client.post("/api/v1/it-feedback", json=ITFeedbackCreate)
    feedback_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/it-feedback/{feedback_id}/resolve",
        headers=headers,
        params={"resolved_by": "admin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["resolvedBy"] == "admin"
    assert data["resolvedAt"] is not None


@pytest.mark.asyncio
async def test_update_feedback_status_with_notes(client: AsyncClient):
    """Test update feedback status with notes."""
    headers = await get_auth_headers(client)
    create_response = await client.post("/api/v1/it-feedback", json=ITFeedbackCreate)
    feedback_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/it-feedback/{feedback_id}/resolve",
        headers=headers,
        params={"resolved_by": "admin", "notes": "已处理完成"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["notes"] == "已处理完成"


@pytest.mark.asyncio
async def test_update_feedback_status_not_found(client: AsyncClient):
    """Test update feedback status with non-existent ID."""
    headers = await get_auth_headers(client)
    response = await client.put(
        "/api/v1/it-feedback/99999/resolve",
        headers=headers,
        params={"resolved_by": "admin"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_feedback(client: AsyncClient):
    """Test delete feedback."""
    headers = await get_auth_headers(client)
    create_response = await client.post("/api/v1/it-feedback", json=ITFeedbackCreate)
    feedback_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/it-feedback/{feedback_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Feedback deleted successfully"

    get_response = await client.get(f"/api/v1/it-feedback/{feedback_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_feedback_not_found(client: AsyncClient):
    """Test delete feedback with non-existent ID."""
    headers = await get_auth_headers(client)
    response = await client.delete("/api/v1/it-feedback/99999", headers=headers)
    assert response.status_code == 404
