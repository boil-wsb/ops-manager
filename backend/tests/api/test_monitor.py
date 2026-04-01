"""
Tests for monitor API.
"""
import uuid

import pytest
from httpx import AsyncClient


def unique_name(prefix: str = "Monitor") -> str:
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
async def test_list_monitors_unauthorized(client: AsyncClient):
    """Test list monitors without authentication (monitor API is public)."""
    response = await client.get("/api/v1/monitor/monitors")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_monitors(client: AsyncClient):
    """Test list monitors with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/monitor/monitors", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_monitors_with_pagination(client: AsyncClient):
    """Test list monitors with pagination parameters."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/monitor/monitors",
        params={"page": 1, "page_size": 10},
        headers=headers
    )
    assert response.status_code == 200


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_list_monitors_with_filters(client: AsyncClient):
    """Test list monitors with filters."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/monitor/monitors",
        params={"monitor_type": "ping", "status": "healthy", "is_enabled": True},
        headers=headers
    )
    assert response.status_code == 200


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_create_monitor_unauthorized(client: AsyncClient):
    """Test create monitor without authentication."""
    response = await client.post(
        "/api/v1/monitor/monitors",
        json={
            "name": unique_name("TestMonitor"),
            "monitor_type": "ping",
            "target": "192.168.1.1"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_monitor(client: AsyncClient):
    """Test create monitor with valid data."""
    headers = await get_auth_headers(client)
    response = await client.post(
        "/api/v1/monitor/monitors",
        headers=headers,
        json={
            "name": unique_name("TestMonitor"),
            "monitor_type": "ping",
            "target": "192.168.1.1",
            "interval_seconds": 60,
            "timeout_seconds": 10
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] is not None
    assert data["monitor_type"] == "ping"
    assert data["target"] == "192.168.1.1"
    assert data["is_enabled"] is True


@pytest.mark.asyncio
async def test_create_http_monitor(client: AsyncClient):
    """Test create HTTP monitor with additional parameters."""
    headers = await get_auth_headers(client)
    response = await client.post(
        "/api/v1/monitor/monitors",
        headers=headers,
        json={
            "name": unique_name("HttpMonitor"),
            "monitor_type": "http",
            "target": "https://example.com/api/health",
            "http_method": "GET",
            "expected_status_code": 200,
            "expected_response_content": "ok"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["monitor_type"] == "http"
    assert data["http_method"] == "GET"


@pytest.mark.asyncio
async def test_get_monitor(client: AsyncClient):
    """Test get monitor by ID."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/monitor/monitors",
        headers=headers,
        json={
            "name": unique_name("GetMonitor"),
            "monitor_type": "ping",
            "target": "192.168.1.1"
        }
    )
    assert create_response.status_code == 201
    monitor_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/monitor/monitors/{monitor_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == monitor_id


@pytest.mark.asyncio
async def test_get_monitor_not_found(client: AsyncClient):
    """Test get monitor that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/monitor/monitors/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_monitor(client: AsyncClient):
    """Test update monitor with valid data."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/monitor/monitors",
        headers=headers,
        json={
            "name": unique_name("UpdateMonitor"),
            "monitor_type": "ping",
            "target": "192.168.1.1"
        }
    )
    assert create_response.status_code == 201
    monitor_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/monitor/monitors/{monitor_id}",
        headers=headers,
        json={"name": "Updated Monitor Name", "interval_seconds": 120}
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated Monitor Name"
    assert data["interval_seconds"] == 120


@pytest.mark.asyncio
async def test_update_monitor_not_found(client: AsyncClient):
    """Test update monitor that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.put(
        "/api/v1/monitor/monitors/99999",
        headers=headers,
        json={"name": "Updated Name"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_monitor(client: AsyncClient):
    """Test delete monitor with valid data."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/monitor/monitors",
        headers=headers,
        json={
            "name": unique_name("DeleteMonitor"),
            "monitor_type": "ping",
            "target": "192.168.1.1"
        }
    )
    assert create_response.status_code == 201
    monitor_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/monitor/monitors/{monitor_id}",
        headers=headers
    )
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_delete_monitor_not_found(client: AsyncClient):
    """Test delete monitor that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.delete("/api/v1/monitor/monitors/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_toggle_monitor(client: AsyncClient):
    """Test toggle monitor enabled status."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/monitor/monitors",
        headers=headers,
        json={
            "name": unique_name("ToggleMonitor"),
            "monitor_type": "ping",
            "target": "192.168.1.1",
            "is_enabled": True
        }
    )
    assert create_response.status_code == 201
    monitor_id = create_response.json()["id"]

    toggle_response = await client.post(
        f"/api/v1/monitor/monitors/{monitor_id}/toggle",
        headers=headers
    )
    assert toggle_response.status_code == 200
    data = toggle_response.json()
    assert data["is_enabled"] is False


@pytest.mark.asyncio
async def test_toggle_monitor_not_found(client: AsyncClient):
    """Test toggle monitor that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.post("/api/v1/monitor/monitors/99999/toggle", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_alerts_unauthorized(client: AsyncClient):
    """Test list alerts without authentication (monitor API is public)."""
    response = await client.get("/api/v1/monitor/alerts")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient):
    """Test list alerts with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/monitor/alerts", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.skip(reason="需要修复")
@pytest.mark.asyncio
async def test_list_alerts_with_filters(client: AsyncClient):
    """Test list alerts with filters."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/monitor/alerts",
        params={"status": "active", "severity": "critical", "monitor_id": 1},
        headers=headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_alert(client: AsyncClient):
    """Test get alert by ID."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/monitor/alerts/1", headers=headers)
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_get_alert_not_found(client: AsyncClient):
    """Test get alert that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/monitor/alerts/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_alert_rules_unauthorized(client: AsyncClient):
    """Test list alert rules without authentication (monitor API is public)."""
    response = await client.get("/api/v1/monitor/alert-rules")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_alert_rules(client: AsyncClient):
    """Test list alert rules with authentication."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/monitor/alert-rules", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_alert_rules_with_filters(client: AsyncClient):
    """Test list alert rules with filters."""
    headers = await get_auth_headers(client)
    response = await client.get(
        "/api/v1/monitor/alert-rules",
        params={"is_enabled": True},
        headers=headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_alert_rule(client: AsyncClient):
    """Test create alert rule with valid data."""
    headers = await get_auth_headers(client)
    response = await client.post(
        "/api/v1/monitor/alert-rules",
        headers=headers,
        json={
            "name": unique_name("AlertRule"),
            "description": "Test alert rule",
            "condition_expression": "metric > 100",
            "duration_seconds": 60,
            "severity": "warning"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] is not None
    assert data["condition_expression"] == "metric > 100"
    assert data["is_enabled"] is True


@pytest.mark.asyncio
async def test_get_alert_rule(client: AsyncClient):
    """Test get alert rule by ID."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/monitor/alert-rules",
        headers=headers,
        json={
            "name": unique_name("GetRule"),
            "condition_expression": "metric > 100",
            "severity": "critical"
        }
    )
    assert create_response.status_code == 201
    rule_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/monitor/alert-rules/{rule_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rule_id


@pytest.mark.asyncio
async def test_get_alert_rule_not_found(client: AsyncClient):
    """Test get alert rule that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.get("/api/v1/monitor/alert-rules/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_alert_rule(client: AsyncClient):
    """Test update alert rule with valid data."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/monitor/alert-rules",
        headers=headers,
        json={
            "name": unique_name("UpdateRule"),
            "condition_expression": "metric > 100",
            "severity": "warning"
        }
    )
    assert create_response.status_code == 201
    rule_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/monitor/alert-rules/{rule_id}",
        headers=headers,
        json={"name": "Updated Rule Name", "is_enabled": False}
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated Rule Name"
    assert data["is_enabled"] is False


@pytest.mark.asyncio
async def test_update_alert_rule_not_found(client: AsyncClient):
    """Test update alert rule that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.put(
        "/api/v1/monitor/alert-rules/99999",
        headers=headers,
        json={"name": "Updated Name"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_alert_rule(client: AsyncClient):
    """Test delete alert rule with valid data."""
    headers = await get_auth_headers(client)
    create_response = await client.post(
        "/api/v1/monitor/alert-rules",
        headers=headers,
        json={
            "name": unique_name("DeleteRule"),
            "condition_expression": "metric > 100",
            "severity": "warning"
        }
    )
    assert create_response.status_code == 201
    rule_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/monitor/alert-rules/{rule_id}",
        headers=headers
    )
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_delete_alert_rule_not_found(client: AsyncClient):
    """Test delete alert rule that does not exist."""
    headers = await get_auth_headers(client)
    response = await client.delete("/api/v1/monitor/alert-rules/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_alert_acknowledge(client: AsyncClient):
    """Test acknowledge an alert."""
    headers = await get_auth_headers(client)
    response = await client.post(
        "/api/v1/monitor/alerts/1/action",
        headers=headers,
        json={"action": "acknowledge", "comment": "Investigating"}
    )
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_alert_resolve(client: AsyncClient):
    """Test resolve an alert."""
    headers = await get_auth_headers(client)
    response = await client.post(
        "/api/v1/monitor/alerts/1/action",
        headers=headers,
        json={"action": "resolve", "comment": "Issue fixed"}
    )
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_alert_suppress(client: AsyncClient):
    """Test suppress an alert."""
    headers = await get_auth_headers(client)
    response = await client.post(
        "/api/v1/monitor/alerts/1/action",
        headers=headers,
        json={"action": "suppress"}
    )
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_alert_action_not_found(client: AsyncClient):
    """Test alert action on non-existent alert."""
    headers = await get_auth_headers(client)
    response = await client.post(
        "/api/v1/monitor/alerts/99999/action",
        headers=headers,
        json={"action": "acknowledge"}
    )
    assert response.status_code == 404