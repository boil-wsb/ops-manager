"""
Tests for notification groups API.
"""
import uuid
import pytest
from httpx import AsyncClient


def unique_name(prefix: str = "Group") -> str:
    """Generate unique name for tests."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def get_auth_headers(client: AsyncClient, username: str = "admin", password: str = "admin123") -> dict:
    """Helper function to get authentication headers via login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.mark.asyncio
async def test_notification_group_crud(client: AsyncClient):
    """Test notification group CRUD operations."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    # Create
    create_response = await client.post(
        "/api/v1/notification-groups",
        headers=headers,
        json={
            "name": unique_name("TestGroup"),
            "description": "Test notification group",
            "notification_type": "feishu",
            "is_active": True
        }
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["name"] is not None
    assert data["notification_type"] == "feishu"
    assert data["is_active"] is True
    assert "members" in data
    group_id = data["id"]

    # Read (list)
    list_response = await client.get("/api/v1/notification-groups", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert "items" in list_data
    assert "total" in list_data
    assert isinstance(list_data["items"], list)

    # Read (get by id)
    get_response = await client.get(f"/api/v1/notification-groups/{group_id}", headers=headers)
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["id"] == group_id
    assert get_data["name"] is not None

    # Update
    update_response = await client.put(
        f"/api/v1/notification-groups/{group_id}",
        headers=headers,
        json={
            "name": unique_name("UpdatedGroup"),
            "description": "Updated description",
            "is_active": False
        }
    )
    assert update_response.status_code == 200
    update_data = update_response.json()
    assert update_data["description"] == "Updated description"
    assert update_data["is_active"] is False

    # Delete
    delete_response = await client.delete(f"/api/v1/notification-groups/{group_id}", headers=headers)
    assert delete_response.status_code == 204

    # Verify deleted
    get_deleted_response = await client.get(f"/api/v1/notification-groups/{group_id}", headers=headers)
    assert get_deleted_response.status_code == 404


@pytest.mark.asyncio
async def test_notification_group_members(client: AsyncClient):
    """Test notification group member management."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    # Create notification group
    group_response = await client.post(
        "/api/v1/notification-groups",
        headers=headers,
        json={
            "name": unique_name("MemberTestGroup"),
            "description": "Group for member test",
            "notification_type": "feishu",
            "is_active": True
        }
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Create a test user to add as member
    user_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": unique_name("MemberUser"),
            "password": "test123456",
            "email": f"{uuid.uuid4().hex[:8]}@example.com",
            "full_name": "Test Member User"
        }
    )
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    # Add member to group
    add_response = await client.post(
        f"/api/v1/notification-groups/{group_id}/members/{user_id}",
        headers=headers
    )
    assert add_response.status_code == 200
    add_data = add_response.json()
    assert "members" in add_data
    member_ids = [m["id"] for m in add_data["members"]]
    assert user_id in member_ids

    # Verify member is in group
    get_group_response = await client.get(f"/api/v1/notification-groups/{group_id}", headers=headers)
    assert get_group_response.status_code == 200
    group_data = get_group_response.json()
    member_ids = [m["id"] for m in group_data["members"]]
    assert user_id in member_ids

    # Remove member from group
    remove_response = await client.delete(
        f"/api/v1/notification-groups/{group_id}/members/{user_id}",
        headers=headers
    )
    assert remove_response.status_code == 200
    remove_data = remove_response.json()
    member_ids = [m["id"] for m in remove_data["members"]]
    assert user_id not in member_ids

    # Cleanup - delete the group
    await client.delete(f"/api/v1/notification-groups/{group_id}", headers=headers)

    # Cleanup - delete the test user
    await client.delete(f"/api/v1/users/{user_id}", headers=headers)


@pytest.mark.asyncio
async def test_notification_group_list_with_filters(client: AsyncClient):
    """Test notification group list with filters."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    # Test with notification_type filter
    response = await client.get(
        "/api/v1/notification-groups",
        params={"notification_type": "feishu"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

    # Test with is_active filter
    response = await client.get(
        "/api/v1/notification-groups",
        params={"is_active": True},
        headers=headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_notification_group_unauthorized(client: AsyncClient):
    """Test notification group endpoints without authentication."""
    # List without auth
    response = await client.get("/api/v1/notification-groups")
    assert response.status_code == 401

    # Create without auth
    response = await client.post(
        "/api/v1/notification-groups",
        json={
            "name": "UnauthorizedGroup",
            "notification_type": "feishu"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_notification_group_not_found(client: AsyncClient):
    """Test notification group operations with non-existent ID."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    # Get non-existent group
    response = await client.get("/api/v1/notification-groups/99999", headers=headers)
    assert response.status_code == 404

    # Update non-existent group
    response = await client.put(
        "/api/v1/notification-groups/99999",
        headers=headers,
        json={"name": "UpdatedName"}
    )
    assert response.status_code == 404

    # Delete non-existent group
    response = await client.delete("/api/v1/notification-groups/99999", headers=headers)
    assert response.status_code == 404

    # Add member to non-existent group
    response = await client.post(
        "/api/v1/notification-groups/99999/members/1",
        headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_member_user_not_found(client: AsyncClient):
    """Test adding non-existent user to notification group."""
    headers = await get_auth_headers(client)
    if not headers:
        pytest.skip("Cannot authenticate for this test")

    # Create notification group
    group_response = await client.post(
        "/api/v1/notification-groups",
        headers=headers,
        json={
            "name": unique_name("AddMemberTest"),
            "notification_type": "feishu"
        }
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Add non-existent user
    response = await client.post(
        f"/api/v1/notification-groups/{group_id}/members/99999",
        headers=headers
    )
    assert response.status_code == 404

    # Cleanup
    await client.delete(f"/api/v1/notification-groups/{group_id}", headers=headers)
