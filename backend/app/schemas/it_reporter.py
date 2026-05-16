from pydantic import BaseModel, Field


class ITReporterRequest(BaseModel):
    report_path: str = Field(..., description="MinIO 中的报告文件路径", validation_alias="reportPath")
    minio_bucket: str = Field(..., description="MinIO 存储桶名称", validation_alias="minioBucket")
    chat_id: str | None = Field(None, description="飞书群聊 ID（可选，不传则从配置读取）", validation_alias="chatId")

    model_config = {"populate_by_name": True}


class ITReporterResponse(BaseModel):
    status: str
    message: str
    data: dict | None = None
