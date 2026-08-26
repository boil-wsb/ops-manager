"""
Tests for audit logs API.
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
async def test_list_audit_logs_unauthorized(client: AsyncClient):
    """Test list audit logs without authentication (audit logs API is public)."""
    response = await client.get("/api/v1/audit-logs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_audit_log_unauthorized(client: AsyncClient):
    """Test get audit log by ID without authentication (audit logs API is public)."""
    response = await client.get("/api/v1/audit-logs/1")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_audit_logs(client: AsyncClient):
    """Test list audit logs with authenticated superuser."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/audit-logs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert "total" in data["pagination"]
    assert "page" in data["pagination"]
    assert "page_size" in data["pagination"]
    assert "pages" in data["pagination"]


@pytest.mark.asyncio
async def test_list_audit_logs_with_filters(client: AsyncClient):
    """Test list audit logs with filters."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/audit-logs",
        params={
            "operation_type": "LOGIN",
            "operation_module": "system",
            "status": "SUCCESS",
            "page": 1,
            "page_size": 10,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 10


@pytest.mark.asyncio
async def test_get_audit_log(client: AsyncClient):
    """Test get audit log by ID with authenticated superuser."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/audit-logs/1", headers=headers)
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_get_audit_log_not_found(client: AsyncClient):
    """Test get audit log by ID that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/audit-logs/99999", headers=headers)
    assert response.status_code == 404
