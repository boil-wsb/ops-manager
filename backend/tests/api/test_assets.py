"""
Tests for assets API.
"""
import pytest
from httpx import AsyncClient


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
async def test_list_assets_unauthorized(client: AsyncClient):
    """Test list assets without authentication returns 401."""
    response = await client.get("/api/v1/assets")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_assets(client: AsyncClient):
    """Test list assets with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/assets", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "items" in data["data"]
    assert "total" in data["data"]


@pytest.mark.asyncio
async def test_list_assets_with_pagination(client: AsyncClient):
    """Test list assets with pagination parameters."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/assets?skip=0&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] >= 0
    assert isinstance(data["data"]["items"], list)


@pytest.mark.asyncio
async def test_list_assets_with_filters(client: AsyncClient):
    """Test list assets with filter parameters."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/assets?asset_type=SERVER&status=ACTIVE",
        headers=headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_labels_unauthorized(client: AsyncClient):
    """Test list labels without authentication (labels API is public)."""
    response = await client.get("/api/v1/labels")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_labels(client: AsyncClient):
    """Test list labels with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/labels", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_labels_with_pagination(client: AsyncClient):
    """Test list labels with pagination parameters."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/labels?skip=0&limit=50", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_assets(client: AsyncClient):
    """Test asset search/filter functionality."""
    headers = await get_auth_headers(client)

    # Test search with keyword filter
    response = await client.get("/api/v1/assets?keyword=test", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "items" in data["data"]
    assert "total" in data["data"]

    # Test search with multiple filters
    response = await client.get(
        "/api/v1/assets?asset_type=SERVER&status=ACTIVE&idc=TestIDC&keyword=server",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Verify items match the filter criteria (if any items exist)
    for item in data["data"]["items"]:
        if item.get("assetType") == "SERVER":
            assert item.get("status") == "ACTIVE"


@pytest.mark.asyncio
async def test_create_and_delete_label(client: AsyncClient):
    """Test asset label management - create and delete label."""
    headers = await get_auth_headers(client)

    # Create a label
    label_data = {
        "name": "test-label",
        "color": "#ff0000",
        "description": "Test label for assets"
    }
    response = await client.post("/api/v1/labels", json=label_data, headers=headers)
    assert response.status_code == 201
    label = response.json()
    assert label["name"] == "test-label"
    assert label["color"] == "#ff0000"
    label_id = label["id"]

    # Verify label was created by listing labels
    response = await client.get("/api/v1/labels", headers=headers)
    assert response.status_code == 200
    labels = response.json()
    label_ids = [l["id"] for l in labels]
    assert label_id in label_ids

    # Delete the label
    response = await client.delete(f"/api/v1/labels/{label_id}", headers=headers)
    assert response.status_code == 204

    # Verify label was deleted
    response = await client.get("/api/v1/labels", headers=headers)
    assert response.status_code == 200
    labels = response.json()
    label_ids = [l["id"] for l in labels]
    assert label_id not in label_ids


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_asset_permissions_unauthorized(client: AsyncClient):
    """Test asset permissions - unauthorized access."""
    # Test list assets without auth
    response = await client.get("/api/v1/assets")
    assert response.status_code == 401

    # Test create asset without auth
    response = await client.post("/api/v1/assets", json={})
    assert response.status_code == 401

    # Test update asset without auth
    response = await client.put("/api/v1/assets/1", json={})
    assert response.status_code == 401

    # Test delete asset without auth
    response = await client.delete("/api/v1/assets/1")
    assert response.status_code == 401


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_create_asset(client: AsyncClient):
    """Test creating a new asset."""
    headers = await get_auth_headers(client)

    # Create a label first for label_ids
    label_data = {"name": "server-label", "color": "#00ff00"}
    label_response = await client.post("/api/v1/labels", json=label_data, headers=headers)
    label_id = label_response.json()["id"]

    # Create asset
    asset_data = {
        "asset_id": f"TEST-SERVER-{__import__('time').time():.0f}",
        "name": "Test Server",
        "asset_type": "SERVER",
        "status": "ACTIVE",
        "ip_address": "192.168.1.100",
        "cpu_cores": 8,
        "memory_gb": 32,
        "disk_gb": 500,
        "os_type": "Linux",
        "os_version": "Ubuntu 22.04",
        "idc": "TestIDC",
        "region": "TestRegion",
        "rack": "TestRack",
        "description": "Test server for unit testing",
        "label_ids": [label_id]
    }
    response = await client.post("/api/v1/assets", json=asset_data, headers=headers)
    assert response.status_code == 201
    asset = response.json()
    assert asset["assetId"] == asset_data["asset_id"]
    assert asset["name"] == asset_data["name"]
    assert asset["assetType"] == "SERVER"
    assert asset["status"] == "ACTIVE"
    assert asset["ipAddress"] == asset_data["ip_address"]
    assert asset["idc"] == asset_data["idc"]

    # Verify asset appears in list
    response = await client.get("/api/v1/assets", headers=headers)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    asset_ids = [item["assetId"] for item in items]
    assert asset_data["asset_id"] in asset_ids


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_update_asset(client: AsyncClient):
    """Test updating an existing asset."""
    headers = await get_auth_headers(client)

    # First create an asset to update
    import time
    asset_id = f"TEST-UPDATE-{time.time():.0f}"
    asset_data = {
        "asset_id": asset_id,
        "name": "Original Name",
        "asset_type": "SERVER",
        "status": "ACTIVE",
        "ip_address": "10.0.0.1"
    }
    create_response = await client.post("/api/v1/assets", json=asset_data, headers=headers)
    assert create_response.status_code == 201
    created_asset = create_response.json()
    asset_db_id = created_asset["id"]

    # Update the asset
    update_data = {
        "name": "Updated Name",
        "status": "MAINTENANCE",
        "ip_address": "10.0.0.2"
    }
    response = await client.put(f"/api/v1/assets/{asset_db_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    updated_asset = response.json()
    assert updated_asset["name"] == "Updated Name"
    assert updated_asset["status"] == "MAINTENANCE"
    assert updated_asset["ipAddress"] == "10.0.0.2"

    # Verify the update persisted
    response = await client.get(f"/api/v1/assets/{asset_db_id}", headers=headers)
    assert response.status_code == 200
    verified_asset = response.json()
    assert verified_asset["name"] == "Updated Name"


@pytest.mark.asyncio
@pytest.mark.skip(reason="需要修复")
async def test_delete_asset(client: AsyncClient):
    """Test deleting an asset."""
    headers = await get_auth_headers(client)

    # First create an asset to delete
    import time
    asset_id = f"TEST-DELETE-{time.time():.0f}"
    asset_data = {
        "asset_id": asset_id,
        "name": "Asset To Delete",
        "asset_type": "SERVER",
        "status": "ACTIVE",
        "ip_address": "10.0.0.99"
    }
    create_response = await client.post("/api/v1/assets", json=asset_data, headers=headers)
    assert create_response.status_code == 201
    created_asset = create_response.json()
    asset_db_id = created_asset["id"]

    # Verify asset exists
    response = await client.get(f"/api/v1/assets/{asset_db_id}", headers=headers)
    assert response.status_code == 200

    # Delete the asset
    response = await client.delete(f"/api/v1/assets/{asset_db_id}", headers=headers)
    assert response.status_code == 204

    # Verify asset no longer exists
    response = await client.get(f"/api/v1/assets/{asset_db_id}", headers=headers)
    assert response.status_code == 404
