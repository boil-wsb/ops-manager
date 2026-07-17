"""CRM sync service.

封装 CRM 增量同步与全量同步的 HTTP 调用逻辑。
同步接口：
- 增量同步: POST {CRM_SYNC_URL}/api/v1/sync/incremental
- 全量同步: POST {CRM_SYNC_URL}/api/v1/sync/full
"""

from typing import Any

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.core.tz import now_shanghai

logger = get_logger(__name__)

# 同步类型常量
SYNC_TYPE_INCREMENTAL = "incremental"
SYNC_TYPE_FULL = "full"

# 同步类型中文名
SYNC_TYPE_LABELS = {
    SYNC_TYPE_INCREMENTAL: "CRM 增量同步",
    SYNC_TYPE_FULL: "CRM 全量同步",
}

# 同步类型对应的 URL 路径
SYNC_TYPE_PATHS = {
    SYNC_TYPE_INCREMENTAL: "/api/v1/sync/incremental",
    SYNC_TYPE_FULL: "/api/v1/sync/full",
}

# 同步类型对应的等待时间（秒）：触发后等待多久查询最终状态
# 增量同步 5 分钟，全量同步 15 分钟
SYNC_WAIT_SECONDS = {
    SYNC_TYPE_INCREMENTAL: 300,
    SYNC_TYPE_FULL: 900,
}


class CRMSyncService:
    """CRM 同步服务，封装对 CRM 同步接口的调用。"""

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or settings.crm_sync_url).rstrip("/")
        self.timeout = timeout or settings.crm_sync_timeout

    def _build_url(self, sync_type: str) -> str:
        path = SYNC_TYPE_PATHS.get(sync_type)
        if not path:
            raise ValueError(f"未知的同步类型: {sync_type}")
        return f"{self.base_url}{path}"

    async def trigger_sync(self, sync_type: str) -> dict[str, Any]:
        """触发 CRM 同步。

        Args:
            sync_type: 同步类型，SYNC_TYPE_INCREMENTAL 或 SYNC_TYPE_FULL

        Returns:
            dict 包含 success/message/data/started_at 等字段
        """
        label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
        url = self._build_url(sync_type)
        started_at = now_shanghai()

        logger.info(
            f"开始触发 {label}: url={url}",
            extra={
                "action": "crm.sync",
                "sync_type": sync_type,
                "url": url,
            },
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url)

            duration_ms = int(
                (now_shanghai() - started_at).total_seconds() * 1000
            )

            if response.status_code < 400:
                # 尝试解析响应体
                try:
                    resp_data = response.json()
                except Exception:
                    resp_data = {"raw": response.text[:500]}

                logger.info(
                    f"{label} 触发成功: status={response.status_code}, duration_ms={duration_ms}",
                    extra={
                        "action": "crm.sync",
                        "sync_type": sync_type,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "response": resp_data,
                    },
                )
                return {
                    "success": True,
                    "message": f"{label} 触发成功",
                    "sync_type": sync_type,
                    "label": label,
                    "url": url,
                    "status_code": response.status_code,
                    "data": resp_data,
                    "started_at": started_at.isoformat(),
                    "duration_ms": duration_ms,
                }

            # HTTP 错误状态码
            error_text = response.text[:500] if response.text else ""
            logger.error(
                f"{label} 触发失败: status={response.status_code}, body={error_text}",
                extra={
                    "action": "crm.sync",
                    "sync_type": sync_type,
                    "status_code": response.status_code,
                    "error": error_text,
                },
            )
            return {
                "success": False,
                "message": f"{label} 触发失败: HTTP {response.status_code}",
                "sync_type": sync_type,
                "label": label,
                "url": url,
                "status_code": response.status_code,
                "error": error_text,
                "started_at": started_at.isoformat(),
                "duration_ms": duration_ms,
            }

        except httpx.TimeoutException:
            duration_ms = int(
                (now_shanghai() - started_at).total_seconds() * 1000
            )
            logger.error(
                f"{label} 触发超时: timeout={self.timeout}s",
                extra={
                    "action": "crm.sync",
                    "sync_type": sync_type,
                    "error": "timeout",
                    "timeout": self.timeout,
                },
            )
            return {
                "success": False,
                "message": f"{label} 触发超时（{self.timeout}s）",
                "sync_type": sync_type,
                "label": label,
                "url": url,
                "error": "timeout",
                "started_at": started_at.isoformat(),
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int(
                (now_shanghai() - started_at).total_seconds() * 1000
            )
            logger.error(
                f"{label} 触发异常: {e}",
                extra={
                    "action": "crm.sync",
                    "sync_type": sync_type,
                    "error": str(e),
                },
            )
            return {
                "success": False,
                "message": f"{label} 触发异常: {str(e)}",
                "sync_type": sync_type,
                "label": label,
                "url": url,
                "error": str(e),
                "started_at": started_at.isoformat(),
                "duration_ms": duration_ms,
            }

    async def trigger_incremental_sync(self) -> dict[str, Any]:
        """触发 CRM 增量同步。"""
        return await self.trigger_sync(SYNC_TYPE_INCREMENTAL)

    async def trigger_full_sync(self) -> dict[str, Any]:
        """触发 CRM 全量同步。"""
        return await self.trigger_sync(SYNC_TYPE_FULL)

    def trigger_sync_sync(self, sync_type: str) -> dict[str, Any]:
        """同步版本的触发方法，用于在飞书回调线程中调用。

        直接使用同步 httpx.Client，避免 asyncio.run 嵌套事件循环问题。
        """
        import httpx as _httpx

        label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
        url = self._build_url(sync_type)
        started_at = now_shanghai()

        logger.info(
            f"开始触发 {label}（同步）: url={url}",
            extra={
                "action": "crm.sync",
                "sync_type": sync_type,
                "url": url,
            },
        )

        try:
            with _httpx.Client(timeout=self.timeout) as client:
                response = client.post(url)

            duration_ms = int(
                (now_shanghai() - started_at).total_seconds() * 1000
            )

            if response.status_code < 400:
                try:
                    resp_data = response.json()
                except Exception:
                    resp_data = {"raw": response.text[:500]}

                logger.info(
                    f"{label} 触发成功（同步）: status={response.status_code}, duration_ms={duration_ms}",
                    extra={
                        "action": "crm.sync",
                        "sync_type": sync_type,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "response": resp_data,
                    },
                )
                return {
                    "success": True,
                    "message": f"{label} 触发成功",
                    "sync_type": sync_type,
                    "label": label,
                    "url": url,
                    "status_code": response.status_code,
                    "data": resp_data,
                    "started_at": started_at.isoformat(),
                    "duration_ms": duration_ms,
                }

            error_text = response.text[:500] if response.text else ""
            logger.error(
                f"{label} 触发失败（同步）: status={response.status_code}, body={error_text}",
                extra={
                    "action": "crm.sync",
                    "sync_type": sync_type,
                    "status_code": response.status_code,
                    "error": error_text,
                },
            )
            return {
                "success": False,
                "message": f"{label} 触发失败: HTTP {response.status_code}",
                "sync_type": sync_type,
                "label": label,
                "url": url,
                "status_code": response.status_code,
                "error": error_text,
                "started_at": started_at.isoformat(),
                "duration_ms": duration_ms,
            }

        except _httpx.TimeoutException:
            duration_ms = int(
                (now_shanghai() - started_at).total_seconds() * 1000
            )
            logger.error(
                f"{label} 触发超时（同步）: timeout={self.timeout}s",
                extra={
                    "action": "crm.sync",
                    "sync_type": sync_type,
                    "error": "timeout",
                    "timeout": self.timeout,
                },
            )
            return {
                "success": False,
                "message": f"{label} 触发超时（{self.timeout}s）",
                "sync_type": sync_type,
                "label": label,
                "url": url,
                "error": "timeout",
                "started_at": started_at.isoformat(),
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int(
                (now_shanghai() - started_at).total_seconds() * 1000
            )
            logger.error(
                f"{label} 触发异常（同步）: {e}",
                extra={
                    "action": "crm.sync",
                    "sync_type": sync_type,
                    "error": str(e),
                },
            )
            return {
                "success": False,
                "message": f"{label} 触发异常: {str(e)}",
                "sync_type": sync_type,
                "label": label,
                "url": url,
                "error": str(e),
                "started_at": started_at.isoformat(),
                "duration_ms": duration_ms,
            }

    def query_sync_status_sync(self, status_url: str) -> dict[str, Any]:
        """查询 CRM 同步任务的状态（同步版本，用于后台线程）。

        Args:
            status_url: 触发同步时返回的 status_url（相对路径，如 /api/v1/sync/status/{task_id}）

        Returns:
            dict 包含 success/status/data 等字段
        """
        import httpx as _httpx

        # 拼接完整 URL
        if status_url.startswith("http://") or status_url.startswith("https://"):
            url = status_url
        else:
            url = f"{self.base_url}{status_url}"

        logger.info(
            f"查询 CRM 同步状态: url={url}",
            extra={"action": "crm.sync.status", "url": url},
        )

        try:
            with _httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)

            if response.status_code < 400:
                try:
                    resp_data = response.json()
                except Exception:
                    resp_data = {"raw": response.text[:500]}

                logger.info(
                    f"查询同步状态成功: status={response.status_code}, data={resp_data}",
                    extra={"action": "crm.sync.status", "status_code": response.status_code, "response": resp_data},
                )
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": resp_data,
                    "url": url,
                }

            error_text = response.text[:500] if response.text else ""
            logger.error(
                f"查询同步状态失败: status={response.status_code}, body={error_text}",
                extra={"action": "crm.sync.status", "status_code": response.status_code, "error": error_text},
            )
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_text,
                "url": url,
            }

        except Exception as e:
            logger.error(
                f"查询同步状态异常: {e}",
                extra={"action": "crm.sync.status", "error": str(e)},
            )
            return {
                "success": False,
                "error": str(e),
                "url": url,
            }


# 单例
_crm_sync_service: CRMSyncService | None = None


def get_crm_sync_service() -> CRMSyncService:
    """获取 CRM 同步服务单例。"""
    global _crm_sync_service
    if _crm_sync_service is None:
        _crm_sync_service = CRMSyncService()
    return _crm_sync_service
