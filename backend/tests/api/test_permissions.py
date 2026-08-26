"""
Tests for permissions API.
"""

import pytest
from httpx import AsyncClient


async def get_auth_headers(
    client: AsyncClient, username: str = "admin", password: str = "admin123"
) -> dict:
    """Helper function to get authentication headers via login."""
    response = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.mark.asyncio
async def test_list_permissions_unauthorized(client: AsyncClient):
    """Test list permissions without authentication."""
    response = await client.get("/api/v1/permissions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_permission_modules_unauthorized(client: AsyncClient):
    """Test get permission modules without authentication."""
    response = await client.get("/api/v1/permissions/modules")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_permission_unauthorized(client: AsyncClient):
    """Test get permission by ID without authentication."""
    response = await client.get("/api/v1/permissions/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_permissions(client: AsyncClient):
    """Test list permissions with authenticated superuser."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/permissions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_list_permissions_with_filters(client: AsyncClient):
    """Test list permissions with module filter."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/permissions", params={"module": "user", "is_active": True}, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_list_permissions_pagination(client: AsyncClient):
    """Test list permissions with pagination."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/permissions", params={"page": 1, "page_size": 10}, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_permission_modules(client: AsyncClient):
    """Test get permission modules with authenticated superuser."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/permissions/modules", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_permission_not_found(client: AsyncClient):
    """Test get permission by ID that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/permissions/99999", headers=headers)
    assert response.status_code == 404
