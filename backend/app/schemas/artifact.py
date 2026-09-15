from pydantic import BaseModel


class ArtifactUploadResponse(BaseModel):
    status: str
    message: str
    bucket: str | None = None
    object_path: str | None = None
    size: int | None = None
    etag: str | None = None
