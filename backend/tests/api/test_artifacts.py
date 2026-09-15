"""产物上传接口测试（multipart 直传）：key 清洗、桶校验、空文件防护、成功上传（mock MinIO）。"""

import io

import pytest
from httpx import AsyncClient

from app.config import settings
from app.core.exceptions import ValidationError
from app.services import artifact_service


@pytest.fixture
def mock_minio(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """mock MinIO 桶检查与流式上传，记录调用参数。"""
    calls: list[dict] = []

    def fake_upload(fileobj, bucket_name: str, object_path: str, length: int, content_type: str):
        fileobj.seek(0)
        calls.append(
            {
                "bucket": bucket_name,
                "object_path": object_path,
                "length": length,
                "content_type": content_type,
                "content": fileobj.read(),
            }
        )
        return {
            "bucket": bucket_name,
            "object_path": object_path,
            "size": length,
            "etag": "deadbeef",
        }

    monkeypatch.setattr(artifact_service, "bucket_exists", lambda b: True)
    monkeypatch.setattr(artifact_service, "upload_fileobj", fake_upload)
    return calls


# ---------- key 清洗 ----------


@pytest.mark.parametrize(
    "bad_key", ["../etc/passwd", "a/../../b", "/abs/path", "a\\..\\..\\b", "   ", "./"]
)
def test_sanitize_rejects_bad_object_path(bad_key: str):
    with pytest.raises(ValidationError):
        artifact_service.sanitize_object_path(bad_key)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("releases/app.zip", "releases/app.zip"),
        ("releases/app.zip/", "releases/app.zip"),
        ("a\\b\\c.zip", "a/b/c.zip"),
    ],
)
def test_sanitize_normalizes(raw: str, expected: str):
    assert artifact_service.sanitize_object_path(raw) == expected


# ---------- 服务层 ----------


def test_upload_rejected_when_bucket_not_exists(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(artifact_service, "bucket_exists", lambda b: False)
    f = io.BytesIO(b"data")
    with pytest.raises(ValidationError):
        artifact_service.upload_artifact(f, "a.zip", "x.zip", bucket="no-such-bucket")


def test_upload_rejected_when_empty_file(mock_minio):
    with pytest.raises(ValidationError):
        artifact_service.upload_artifact(io.BytesIO(b""), "a.zip", "x.zip")


def test_upload_success_with_default_bucket(mock_minio):
    result = artifact_service.upload_artifact(io.BytesIO(b"hello world"), "app.zip", "releases/app.zip")
    assert result["etag"] == "deadbeef"
    assert result["bucket"] == settings.artifact_upload_default_bucket
    assert mock_minio[0]["length"] == 11
    assert mock_minio[0]["object_path"] == "releases/app.zip"


# ---------- 接口层 ----------


@pytest.mark.asyncio
async def test_api_upload_success(client: AsyncClient, mock_minio):
    resp = await client.post(
        "/api/v1/artifacts/upload",
        files={"file": ("app.zip", b"artifact-bytes-123", "application/zip")},
        data={"object_path": "releases/app.zip"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["bucket"] == settings.artifact_upload_default_bucket
    assert data["object_path"] == "releases/app.zip"
    assert data["size"] == 18
    assert data["etag"] == "deadbeef"
    assert mock_minio[0]["content"] == b"artifact-bytes-123"


@pytest.mark.asyncio
async def test_api_upload_bad_object_path(client: AsyncClient, mock_minio):
    resp = await client.post(
        "/api/v1/artifacts/upload",
        files={"file": ("app.zip", b"x", "application/zip")},
        data={"object_path": "../escape.zip"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_api_upload_bucket_not_exists(client: AsyncClient, mock_minio, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(artifact_service, "bucket_exists", lambda b: False)
    resp = await client.post(
        "/api/v1/artifacts/upload",
        files={"file": ("app.zip", b"x", "application/zip")},
        data={"object_path": "x.zip", "bucket": "no-such-bucket"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_api_upload_empty_file(client: AsyncClient, mock_minio):
    resp = await client.post(
        "/api/v1/artifacts/upload",
        files={"file": ("app.zip", b"", "application/zip")},
        data={"object_path": "x.zip"},
    )
    assert resp.status_code == 422
