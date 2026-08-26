"""
Prometheus 配置仓库远端同步定时任务

每 2 小时检查 git-repos/prometheus 与 GitLab 远端是否同步：
- 远端较新（behind>0）且本地无未推送提交（ahead==0）且工作区无脏改动 → 自动 pull 拉到本地。
- 本地较新（ahead>0）或有脏改动 → 不拉取，由前端「提交并推送」按钮处理。
"""

import asyncio

from app.core.logging import get_logger
from app.services.git_repo.git_repo_service import get_git_repo_service

logger = get_logger(__name__)


async def _ensure_clone_async():
    return await asyncio.to_thread(get_git_repo_service().ensure_clone)


async def sync_git_repo_with_remote_task() -> dict:
    """与远端同步配置（每 2 小时）。"""
    svc = get_git_repo_service()
    try:
        if not svc.is_cloned():
            await _ensure_clone_async()
    except Exception as e:
        logger.error(f"同步任务克隆失败: {e}", extra={"action": "git_sync"})
        return {"status": "skip", "reason": "clone_failed", "error": str(e)}

    try:
        sync = await asyncio.to_thread(svc.get_sync_status)
    except Exception as e:
        logger.error(f"同步状态检查失败: {e}", extra={"action": "git_sync"})
        return {"status": "failed", "error": str(e)}

    ahead = sync.get("ahead", 0)
    behind = sync.get("behind", 0)
    dirty = sync.get("dirty", False)

    action = "noop_synced"
    if behind > 0 and ahead == 0 and not dirty:
        try:
            await asyncio.to_thread(svc.pull)
            action = "synced_remote_to_local"
            logger.info(
                f"远端较新，已同步到本地 (behind={behind})",
                extra={"action": "git_sync", "behind": behind},
            )
        except Exception as e:
            logger.error(f"远端同步到本地失败: {e}", extra={"action": "git_sync"})
            return {"status": "failed", "error": str(e), "ahead": ahead, "behind": behind}
    elif ahead > 0 or dirty:
        action = "skip_local_newer"

    return {
        "status": "success",
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty,
        "action": action,
        "result_summary": action,
    }
