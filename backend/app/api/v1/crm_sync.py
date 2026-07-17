"""CRM sync API routes.

提供触发 CRM 同步的接口：
- POST /api/v1/crm/sync/incremental  触发增量同步
- POST /api/v1/crm/sync/full         触发全量同步
- POST /api/v1/crm/sync               通用触发接口，通过 sync_type 参数指定

接口无需权限校验（按需求要求）。
"""

import asyncio

from fastapi import APIRouter, Body, Query

from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.services.crm.sync_service import (
    SYNC_TYPE_FULL,
    SYNC_TYPE_INCREMENTAL,
    SYNC_TYPE_LABELS,
    get_crm_sync_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/crm", tags=["CRM 同步"])


@router.post("/sync/incremental")
async def trigger_incremental_sync():
    """触发 CRM 增量同步。

    调用 CRM 同步接口：POST {CRM_SYNC_URL}/api/v1/sync/incremental
    """
    service = get_crm_sync_service()
    result = await service.trigger_incremental_sync()
    return result


@router.post("/sync/full")
async def trigger_full_sync():
    """触发 CRM 全量同步。

    调用 CRM 同步接口：POST {CRM_SYNC_URL}/api/v1/sync/full
    """
    service = get_crm_sync_service()
    result = await service.trigger_full_sync()
    return result


@router.post("/sync")
async def trigger_sync(
    sync_type: str = Query(..., description="同步类型: incremental 或 full"),
):
    """通用 CRM 同步触发接口。

    通过 query 参数 sync_type 指定同步类型。
    """
    if sync_type not in (SYNC_TYPE_INCREMENTAL, SYNC_TYPE_FULL):
        return {
            "success": False,
            "message": f"无效的同步类型: {sync_type}，仅支持 incremental 或 full",
            "sync_type": sync_type,
        }

    service = get_crm_sync_service()
    result = await service.trigger_sync(sync_type)
    return result


@router.post("/sync/async")
async def trigger_sync_async(
    payload: dict = Body(default={}, description="可选参数，sync_type 指定同步类型"),
):
    """异步触发 CRM 同步（立即返回，后台执行）。

    用于飞书卡片回调场景：回调立即响应飞书，同步在后台执行，
    完成后通过更新飞书卡片通知结果。

    请求体示例：
    ```
    {"sync_type": "incremental", "open_message_id": "om_xxx"}
    ```
    - sync_type: 同步类型（incremental 或 full），必填
    - open_message_id: 飞书卡片消息 ID，可选，用于完成后更新卡片
    - operator_open_id: 操作者 open_id，可选，用于日志记录
    """
    sync_type = payload.get("sync_type", "")
    open_message_id = payload.get("open_message_id")
    operator_open_id = payload.get("operator_open_id")

    if sync_type not in (SYNC_TYPE_INCREMENTAL, SYNC_TYPE_FULL):
        return {
            "success": False,
            "message": f"无效的同步类型: {sync_type}，仅支持 incremental 或 full",
            "sync_type": sync_type,
        }

    label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
    triggered_at = now_shanghai().isoformat()

    logger.info(
        f"异步触发 {label}: open_message_id={open_message_id}, operator={operator_open_id}",
        extra={
            "action": "crm.sync.async",
            "sync_type": sync_type,
            "open_message_id": open_message_id,
            "operator_open_id": operator_open_id,
        },
    )

    # 启动后台任务执行同步 + 卡片更新
    asyncio.create_task(
        _run_sync_and_update_card(sync_type, open_message_id, operator_open_id)
    )

    return {
        "success": True,
        "message": f"{label} 已触发，正在后台执行",
        "sync_type": sync_type,
        "label": label,
        "open_message_id": open_message_id,
        "triggered_at": triggered_at,
        "status": "running",
    }


async def _run_sync_and_update_card(
    sync_type: str,
    open_message_id: str | None,
    operator_open_id: str | None,
) -> None:
    """后台执行 CRM 同步并更新飞书卡片状态。

    流程：
    1. 先更新卡片为"同步中"状态
    2. 执行 CRM 同步调用
    3. 根据结果更新卡片为"成功"或"失败"状态
    """
    from app.services.crm.card_updater import update_card_to_sync_result, update_card_to_syncing

    label = SYNC_TYPE_LABELS.get(sync_type, sync_type)

    # 1. 更新卡片为同步中
    if open_message_id:
        try:
            await update_card_to_syncing(open_message_id, sync_type)
        except Exception as e:
            logger.warning(
                f"更新卡片为同步中状态失败: {e}",
                extra={
                    "action": "crm.sync.card_update",
                    "open_message_id": open_message_id,
                    "error": str(e),
                },
            )

    # 2. 执行同步
    service = get_crm_sync_service()
    result = await service.trigger_sync(sync_type)

    # 3. 更新卡片为最终结果
    if open_message_id:
        try:
            await update_card_to_sync_result(open_message_id, sync_type, result)
        except Exception as e:
            logger.error(
                f"更新卡片为最终结果状态失败: {e}",
                extra={
                    "action": "crm.sync.card_update",
                    "open_message_id": open_message_id,
                    "error": str(e),
                },
            )

    logger.info(
        f"{label} 后台执行完成: success={result.get('success')}",
        extra={
            "action": "crm.sync.async",
            "sync_type": sync_type,
            "success": result.get("success"),
            "open_message_id": open_message_id,
            "operator_open_id": operator_open_id,
        },
    )
