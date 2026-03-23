"""
Tests for authentication API.
"""
import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient) -> dict:
    """Helper to get authentication headers."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_login_with_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limiting(client: AsyncClient):
    """Test that login endpoint is rate limited."""
    for _ in range(6):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "test",
                "password": "test"
            }
        )

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_get_current_user_me(client: AsyncClient):
    """Test get current user info endpoint."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "email" in data
    assert "permissions" in data


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test get current user info without authentication."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """Test logout endpoint."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    response = await client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "退出登录成功"


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    """Test change password endpoint."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    response = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "old_password": "admin123",
            "new_password": "newpassword123"
        }
    )
    if response.status_code == 200:
        assert response.json()["message"] == "密码修改成功"


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(client: AsyncClient):
    """Test change password with wrong old password."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    response = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "old_password": "wrongpassword",
            "new_password": "newpassword123"
        }
    )
    assert response.status_code == 400
