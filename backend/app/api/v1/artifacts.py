from fastapi import APIRouter, File, Form, Request, UploadFile

from app.core.audit import audit_log
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.schemas.artifact import ArtifactUploadResponse
from app.services.artifact_service import upload_artifact

router = APIRouter(prefix="/artifacts", tags=["产物上传"])
logger = get_logger(__name__)


@router.post("/upload", response_model=ArtifactUploadResponse)
@limiter.limit("30/minute")
@audit_log(operation_type="ARTIFACT_UPLOAD", module="artifact")
async def upload_artifact_api(
    request: Request,
    file: UploadFile = File(..., description="产物文件"),
    object_path: str = Form(..., description="MinIO 目标对象路径（key）"),
    bucket: str | None = Form(None, description="目标桶（可选，缺省用 ARTIFACT_UPLOAD_DEFAULT_BUCKET）"),
):
    """内网产物上传：curl/客户端直接携带文件内容（multipart），流式转发到 MinIO。

    仅信任网段内免 JWT（AUTH_EXCLUDED_PATHS），网段外需携带有效 JWT。
    """
    result = await run_upload(file, object_path, bucket)
    return ArtifactUploadResponse(status="success", message="上传成功", **result)


async def run_upload(file: UploadFile, object_path: str, bucket: str | None) -> dict:
    """在线程池中执行同步 MinIO 上传，避免阻塞事件循环。"""
    import asyncio

    return await asyncio.to_thread(
        upload_artifact,
        file.file,
        file.filename,
        object_path,
        bucket,
    )
