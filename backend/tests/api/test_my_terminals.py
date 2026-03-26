"""
Tests for Monitor My Terminals API.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_my_terminals_requires_auth(client: AsyncClient):
    """Test that my-terminals endpoint requires authentication."""
    response = await client.get("/api/v1/monitor/my-terminals")
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_get_my_terminals(client: AsyncClient):
    """Test get user's terminal monitors."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )

    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        if token:
            response = await client.get(
                "/api/v1/monitor/my-terminals",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_my_terminals_pagination(client: AsyncClient):
    """Test my-terminals with pagination parameters."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )

    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        if token:
            response = await client.get(
                "/api/v1/monitor/my-terminals?skip=0&limit=10",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data