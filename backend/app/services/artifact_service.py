"""产物上传服务：multipart 文件流式转发到 MinIO。

安全约束：
- object_path 清洗：拒绝 .. 段与绝对路径，统一 / 分隔；
- 目标桶必须已存在（不自动创建）；
- 文件内容经 put_object 流式转发，不占内存。
"""

from pathlib import PurePosixPath

from app.config import settings
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.integrations.minio.client import bucket_exists, upload_fileobj

logger = get_logger(__name__)


def sanitize_object_path(object_path: str) -> str:
    """清洗 MinIO 对象 key：统一 / 分隔，拒绝 .. 与绝对路径。"""
    normalized = object_path.strip().replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValidationError(detail=f"object_path 非法: {object_path}（不允许绝对路径或 .. 穿越）")
    cleaned = "/".join(part for part in pure.parts if part not in ("", "."))
    if not cleaned:
        raise ValidationError(detail=f"object_path 非法: {object_path}")
    return cleaned


def upload_artifact(
    fileobj, filename: str | None, object_path: str, bucket: str | None = None
) -> dict:
    """将上传的文件对象流式转发到 MinIO，返回 {"bucket","object_path","size","etag"}。

    fileobj 为可 seek 的文件对象（FastAPI UploadFile.file）。
    """
    target_bucket = (bucket or settings.artifact_upload_default_bucket).strip()
    if not target_bucket:
        raise ValidationError(detail="目标桶为空")
    if not bucket_exists(target_bucket):
        raise ValidationError(detail=f"目标桶不存在: {target_bucket}")

    key = sanitize_object_path(object_path)

    fileobj.seek(0, 2)
    length = fileobj.tell()
    fileobj.seek(0)
    if length <= 0:
        raise ValidationError(detail="上传文件为空")

    content_type = "application/octet-stream"
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        guessed = {
            "zip": "application/zip",
            "gz": "application/gzip",
            "tar": "application/x-tar",
            "pdf": "application/pdf",
            "html": "text/html",
            "txt": "text/plain",
            "json": "application/json",
        }.get(ext)
        if guessed:
            content_type = guessed

    result = upload_fileobj(fileobj, target_bucket, key, length=length, content_type=content_type)
    logger.info(
        f"产物上传完成: {filename} -> {target_bucket}/{key}",
        extra={"action": "artifact.upload", "bucket": target_bucket, "object_path": key, "size": length},
    )
    return result
