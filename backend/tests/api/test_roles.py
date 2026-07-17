"""
Tests for roles API.
"""
import uuid

import pytest
from httpx import AsyncClient


def unique_name(prefix: str = "Test") -> str:
    """Generate unique name for tests."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


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
async def test_list_roles_unauthorized(client: AsyncClient):
    """Test list roles without authentication."""
    response = await client.get("/api/v1/roles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_roles(client: AsyncClient):
    """Test list roles with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/roles", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_list_roles_with_pagination(client: AsyncClient):
    """Test list roles with pagination parameters."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/roles?page=1&page_size=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_role_unauthorized(client: AsyncClient):
    """Test get role without authentication."""
    response = await client.get("/api/v1/roles/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_role_not_found(client: AsyncClient):
    """Test get role that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/roles/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_role_unauthorized(client: AsyncClient):
    """Test create role without authentication."""
    response = await client.post(
        "/api/v1/roles",
        json={"name": "Test Role", "description": "Test description"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_role(client: AsyncClient):
    """Test create role with valid data."""
    headers = await get_auth_headers(client)
    role_name = unique_name("Role")
    response = await client.post(
        "/api/v1/roles",
        headers=headers,
        json={
            "name": role_name,
            "description": "Test role description"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == role_name
    assert data["description"] == "Test role description"
    assert data["is_system"] is False
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_role_duplicate_name(client: AsyncClient):
    """Test create role with duplicate name."""
    headers = await get_auth_headers(client)
    role_data = {
        "name": "Duplicate Role",
        "description": "Test role"
    }
    await client.post("/api/v1/roles", headers=headers, json=role_data)
    response = await client.post("/api/v1/roles", headers=headers, json=role_data)
    assert response.status_code == 400
