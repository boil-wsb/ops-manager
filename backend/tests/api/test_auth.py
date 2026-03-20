"""
Tests for authentication API.
"""
import pytest
from httpx import AsyncClient


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
