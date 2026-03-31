"""
Tests for assets API.
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


@pytest.mark.asyncio
async def test_list_assets_unauthorized(client: AsyncClient):
    """Test list assets without authentication returns 401."""
    response = await client.get("/api/v1/assets")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_assets(client: AsyncClient):
    """Test list assets with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/assets", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "items" in data["data"]
    assert "total" in data["data"]


@pytest.mark.asyncio
async def test_list_assets_with_pagination(client: AsyncClient):
    """Test list assets with pagination parameters."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/assets?skip=0&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] >= 0
    assert isinstance(data["data"]["items"], list)


@pytest.mark.asyncio
async def test_list_assets_with_filters(client: AsyncClient):
    """Test list assets with filter parameters."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/assets?asset_type=SERVER&status=ACTIVE",
        headers=headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_labels_unauthorized(client: AsyncClient):
    """Test list labels without authentication (labels API is public)."""
    response = await client.get("/api/v1/labels")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_labels(client: AsyncClient):
    """Test list labels with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/labels", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_labels_with_pagination(client: AsyncClient):
    """Test list labels with pagination parameters."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/labels?skip=0&limit=50", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
