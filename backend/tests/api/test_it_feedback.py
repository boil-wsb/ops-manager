"""
Tests for IT Feedback API.
"""
import pytest
from httpx import AsyncClient


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
    for _ in range(3):
        await client.post("/api/v1/it-feedback", json=ITFeedbackCreate)

    response = await client.get("/api/v1/it-feedback?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) == 2


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
