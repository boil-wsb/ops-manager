"""
Tests for navigation API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_public_navigation(client: AsyncClient):
    """Test get public navigation links endpoint."""
    response = await client.get("/api/v1/navigation/public")
    assert response.status_code == 200
    data = response.json()
    assert "groups" in data
    assert isinstance(data["groups"], list)


@pytest.mark.asyncio
async def test_list_navigation_unauthorized(client: AsyncClient):
    """Test list navigation links without authentication returns 401."""
    response = await client.get("/api/v1/navigation")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_navigation(client: AsyncClient, db_session):
    """Test list navigation links endpoint with authentication."""
    login_response = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    response = await client.get("/api/v1/navigation", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)
