"""
Tests for users API.
"""
import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, username: str = "admin", password: str = "admin123") -> dict:
    """Helper function to get authentication headers via login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.mark.asyncio
async def test_list_users_unauthorized(client: AsyncClient):
    """Test list users without authentication."""
    response = await client.get("/api/v1/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient):
    """Test list users with authenticated superuser."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_list_users_with_pagination(client: AsyncClient):
    """Test list users with pagination parameters."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/users",
        params={"page": 1, "page_size": 10},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_list_users_with_keyword_filter(client: AsyncClient):
    """Test list users with keyword filter."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/users",
        params={"keyword": "admin"},
        headers=headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_user_unauthorized(client: AsyncClient):
    """Test get user by ID without authentication."""
    response = await client.get("/api/v1/users/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient):
    """Test get user by ID with authenticated superuser."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/users/1", headers=headers)
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    """Test get user by ID that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/users/99999", headers=headers)
    assert response.status_code == 404