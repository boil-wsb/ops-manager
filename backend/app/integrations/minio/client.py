import os
from datetime import timedelta

from minio import Minio

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_minio_client: Minio | None = None


def get_minio_client() -> Minio:
    global _minio_client
    if _minio_client is None:
        endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
        _minio_client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _minio_client


def download_file(bucket_name: str, object_path: str, local_dir: str = "downloads") -> str:
    client = get_minio_client()
    os.makedirs(local_dir, exist_ok=True)
    local_filename = os.path.basename(object_path)
    local_filepath = os.path.join(local_dir, local_filename)
    client.fget_object(bucket_name, object_path, local_filepath)
    return local_filepath


def generate_presigned_url(
    bucket_name: str, object_path: str, expires_hours: int = 2
) -> str | None:
    try:
        client = get_minio_client()
        return client.presigned_get_object(
            bucket_name, object_path, expires=timedelta(hours=expires_hours)
        )
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None


def get_file_size(filepath: str) -> int:
    return os.path.getsize(filepath)
