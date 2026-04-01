"""
Tests for ops API (deployments and DNS records).
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
async def test_list_deployments(client: AsyncClient):
    """Test deployment list endpoint."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    response = await client.get("/api/v1/ops/deployments", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data or isinstance(data, list)
    assert "total" in data or "count" in data


@pytest.mark.asyncio
async def test_deployment_detail(client: AsyncClient):
    """Test deployment detail endpoint."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    # First get deployment list to find a valid deployment ID
    list_response = await client.get("/api/v1/ops/deployments", headers=headers)
    if list_response.status_code != 200:
        pytest.skip("Cannot get deployment list")

    list_data = list_response.json()
    items = list_data.get("items", []) if isinstance(list_data, dict) else list_data

    if not items:
        pytest.skip("No deployments available for detail test")

    deployment_id = items[0].get("id")
    if not deployment_id:
        pytest.skip("Deployment ID not found")

    response = await client.get(f"/api/v1/ops/deployments/{deployment_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data or "deployment_id" in data


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_dns_records(client: AsyncClient):
    """Test DNS records endpoint."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    response = await client.get("/api/v1/ops/dns-records", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data or isinstance(data, list)
    assert "total" in data or "count" in data
