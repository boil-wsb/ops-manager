"""
Tests for users API.
"""

import uuid

import pytest
from httpx import AsyncClient


def unique_name(prefix: str = "User") -> str:
    """Generate unique name for tests."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


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
        "/api/v1/users", params={"page": 1, "page_size": 10}, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_list_users_with_keyword_filter(client: AsyncClient):
    """Test list users with keyword filter."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/users", params={"keyword": "admin"}, headers=headers)
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


@pytest.mark.asyncio
async def test_create_user_unauthorized(client: AsyncClient):
    """Test create user without authentication."""
    response = await client.post(
        "/api/v1/users",
        json={
            "username": unique_name("CreateUser"),
            "password": "test123456",
            "email": "test@example.com",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    """Test create user with valid data."""
    headers = await get_auth_headers(client)
    response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": unique_name("CreateUser"),
            "password": "test123456",
            "email": f"{uuid.uuid4().hex[:8]}@example.com",
            "full_name": "Test Create User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] is not None
    assert data["email"] is not None
    assert data["is_active"] is True
    assert data["is_superuser"] is False


@pytest.mark.asyncio
async def test_create_user_duplicate_username(client: AsyncClient):
    """Test create user with duplicate username."""
    headers = await get_auth_headers(client)
    username = unique_name("DupUser")
    user_data = {
        "username": username,
        "password": "test123456",
        "email": f"{uuid.uuid4().hex[:8]}@example.com",
    }
    await client.post("/api/v1/users", headers=headers, json=user_data)
    response = await client.post("/api/v1/users", headers=headers, json=user_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_user_unauthorized(client: AsyncClient):
    """Test update user without authentication."""
    response = await client.put("/api/v1/users/1", json={"full_name": "Updated Name"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient):
    """Test update user with valid data."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": unique_name("UpdateUser"),
            "password": "test123456",
            "email": f"{uuid.uuid4().hex[:8]}@example.com",
            "full_name": "Original Name",
        },
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/users/{user_id}", headers=headers, json={"full_name": "Updated Name"}
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_not_found(client: AsyncClient):
    """Test update user that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.put(
        "/api/v1/users/99999", headers=headers, json={"full_name": "Updated Name"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_unauthorized(client: AsyncClient):
    """Test delete user without authentication."""
    response = await client.delete("/api/v1/users/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient):
    """Test delete user with valid data."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": unique_name("DeleteUser"),
            "password": "test123456",
            "email": f"{uuid.uuid4().hex[:8]}@example.com",
        },
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient):
    """Test delete user that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.delete("/api/v1/users/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_role_to_user_unauthorized(client: AsyncClient):
    """Test assign role to user without authentication."""
    response = await client.post("/api/v1/users/1/roles", json=[1])
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_assign_role_to_user(client: AsyncClient):
    """Test assign role to user with valid data."""
    headers = await get_auth_headers(client)
    create_user_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": unique_name("RoleUser"),
            "password": "test123456",
            "email": f"{uuid.uuid4().hex[:8]}@example.com",
        },
    )
    assert create_user_response.status_code == 201
    user_id = create_user_response.json()["id"]

    create_role_response = await client.post(
        "/api/v1/roles",
        headers=headers,
        json={"name": unique_name("TestRole"), "description": "Test role for assignment"},
    )
    assert create_role_response.status_code == 201
    role_id = create_role_response.json()["id"]

    assign_response = await client.post(
        f"/api/v1/users/{user_id}/roles", headers=headers, json=[role_id]
    )
    assert assign_response.status_code == 200
    data = assign_response.json()
    assert data["user_id"] == user_id
    assert role_id in [r["id"] for r in data["roles"]]


@pytest.mark.asyncio
async def test_assign_role_user_not_found(client: AsyncClient):
    """Test assign role to user that does not exist."""
    headers = await get_auth_headers(client)
    create_role_response = await client.post(
        "/api/v1/roles",
        headers=headers,
        json={"name": unique_name("TestRole"), "description": "Test role"},
    )
    assert create_role_response.status_code == 201
    role_id = create_role_response.json()["id"]

    response = await client.post("/api/v1/users/99999/roles", headers=headers, json=[role_id])
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_role_role_not_found(client: AsyncClient):
    """Test assign role that does not exist to user."""
    headers = await get_auth_headers(client)
    create_user_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": unique_name("RoleUser"),
            "password": "test123456",
            "email": f"{uuid.uuid4().hex[:8]}@example.com",
        },
    )
    assert create_user_response.status_code == 201
    user_id = create_user_response.json()["id"]

    response = await client.post(f"/api/v1/users/{user_id}/roles", headers=headers, json=[99999])
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_user_permissions(client: AsyncClient):
    """Test user permissions via auth me endpoint."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "permissions" in data
    assert isinstance(data["permissions"], list)
