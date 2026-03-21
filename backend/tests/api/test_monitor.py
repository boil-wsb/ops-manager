"""
Tests for monitor API.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_monitors_unauthorized(client: AsyncClient):
    """Test list monitors without authentication (monitor API is public)."""
    response = await client.get("/api/v1/monitor/monitors")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_alerts_unauthorized(client: AsyncClient):
    """Test list alerts without authentication (monitor API is public)."""
    response = await client.get("/api/v1/monitor/alerts")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_alert_rules_unauthorized(client: AsyncClient):
    """Test list alert rules without authentication (monitor API is public)."""
    response = await client.get("/api/v1/monitor/alert-rules")
    assert response.status_code == 200