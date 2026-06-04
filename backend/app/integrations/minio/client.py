import os
from datetime import timedelta

from minio import Minio

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_minio_client: Minio | None = None

SINGLE_URL_MAX_EXPIRES_HOURS = 168


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
        actual_hours = min(expires_hours, SINGLE_URL_MAX_EXPIRES_HOURS)
        if actual_hours < expires_hours:
            logger.info(
                f"预签名URL时长已限制: {expires_hours}h -> {actual_hours}h",
                extra={
                    "action": "minio.download",
                    "expires_hours": expires_hours,
                    "actual_hours": actual_hours,
                },
            )
        return client.presigned_get_object(
            bucket_name, object_path, expires=timedelta(hours=actual_hours)
        )
    except Exception as e:
        logger.error(f"生成预签名URL失败: {e}", extra={"action": "minio.download", "error": str(e)})
        return None


def find_latest_object_by_prefix(bucket_name: str, prefix: str) -> str | None:
    try:
        client = get_minio_client()
        objects = list(client.list_objects(bucket_name, prefix=prefix, recursive=True))
        if not objects:
            return None
        latest = max(objects, key=lambda o: o.last_modified)
        return latest.object_name
    except Exception as e:
        logger.error(
            f"按前缀查找最新对象失败: '{prefix}'",
            extra={"action": "minio.download", "prefix": prefix, "error": str(e)},
        )
        return None


def get_file_size(filepath: str) -> int:
    return os.path.getsize(filepath)
