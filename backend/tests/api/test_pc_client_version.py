"""
Tests for PC Client Version API - Download functionality.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_download_requires_auth(client: AsyncClient):
    """Test that download endpoint requires authentication."""
    response = await client.get("/api/v1/pc-client-version/download")
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_download_personalized_package(client: AsyncClient):
    """Test download personalized PC client package."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )

    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        if token:
            response = await client.get(
                "/api/v1/pc-client-version/download",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/zip"
            assert "attachment" in response.headers.get("content-disposition", "")
            assert "pcinfo_" in response.headers.get("content-disposition", "")