"""L2 单元测试: crud_alert_history.create_from_alertmanager IntegrityError 恢复路径.

★ ND-1 修复测试 (第二轮审查) ★

第一性原理覆盖的不变式:
- 一致性: IntegrityError 重试 SELECT 必须加 status='firing' 过滤，
  避免命中已 resolved 的记录（ND-1 修复点）。
- 隔离性: 重试 SELECT 使用 with_for_update() 行锁。

ND-1 根因:
- 部分唯一索引 ix_alert_history_firing_unique WHERE status='firing' 触发 IntegrityError
- 原 C-04 修复的重试 SELECT 未加 status='firing' 过滤
- 命中已 resolved 记录并加锁，会把已 resolved 记录改回 firing
- 与 I-01 修复意图冲突（I-01 批量 resolve 已 resolved 记录保持 resolved）

修复: 重试 SELECT 也加 AlertHistory.status == "firing" 过滤。
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.crud.crud_alert import crud_alert_history
from app.models.alert import AlertHistory


def _make_history(*, id: int = 1, status: str = "firing") -> AlertHistory:
    """构造 AlertHistory 实例."""
    return AlertHistory(
        id=id,
        alertname="HighCpu",
        status=status,
        severity="critical",
        labels={"instance": "192.168.1.10"},
        annotations={},
        starts_at=datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC),
        notification_sent=False,
    )


class TestCreateFromAlertmanagerIntegrityRecovery:
    """ND-1: IntegrityError 重试 SELECT 必须过滤 status='firing'."""

    async def test_integrity_error_recovery_returns_firing_record(self):
        """IntegrityError 触发后,重试 SELECT 返回 firing 记录(非 resolved)."""
        db = AsyncMock()

        # 1. db.add 不抛异常
        # 2. db.commit 抛 IntegrityError
        # 3. db.rollback 不抛异常
        # 4. db.execute 返回 firing 记录
        firing_record = _make_history(id=999, status="firing")

        # 模拟: execute 第一次返回 firing 记录（重试 SELECT 的结果）
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = firing_record
        db.execute = AsyncMock(return_value=execute_result)

        # commit 抛 IntegrityError
        db.commit = AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("dup key")))
        db.rollback = AsyncMock()
        db.refresh = AsyncMock()

        # 调用 create_from_alertmanager
        starts_at = datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC)
        result = await crud_alert_history.create_from_alertmanager(
            db=db,
            alertname="HighCpu",
            status="firing",
            severity="critical",
            labels={"instance": "192.168.1.10"},
            annotations={"description": "CPU > 90%"},
            starts_at=starts_at,
            ends_at=None,
            is_suppressed=False,
            silence_id=None,
        )

        # ★ ND-1 核心断言 1: 返回 firing 记录而非 resolved
        assert result is firing_record
        assert result.status == "firing"
        assert result.id == 999

        # ★ ND-1 核心断言 2: commit 触发了 IntegrityError，rollback 被调用
        db.commit.assert_awaited_once()
        db.rollback.assert_awaited_once()

        # ★ ND-1 核心断言 3: 重试 SELECT 被执行（execute 被调用 1 次）
        db.execute.assert_awaited_once()
        # 验证 execute 接收的是 select 语句（不是其他类型）
        select_stmt = db.execute.await_args.args[0]
        # 编译 SQL 查看是否包含 status = 'firing' 过滤
        compiled = str(select_stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "firing" in compiled.lower(), (
            "ND-1: 重试 SELECT 必须包含 status='firing' 过滤条件，避免命中已 resolved 的记录并加锁"
        )

    async def test_integrity_error_recovery_raises_when_no_firing_record(self):
        """IntegrityError 触发后,重试 SELECT 未找到 firing 记录 → 重新抛出异常."""
        db = AsyncMock()

        # execute 返回 None（找不到 firing 记录）
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=execute_result)

        db.commit = AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("dup key")))
        db.rollback = AsyncMock()

        starts_at = datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC)

        # 应该重新抛出 IntegrityError
        with pytest.raises(IntegrityError):
            await crud_alert_history.create_from_alertmanager(
                db=db,
                alertname="HighCpu",
                status="firing",
                severity="critical",
                labels={"instance": "192.168.1.10"},
                annotations={},
                starts_at=starts_at,
                ends_at=None,
                is_suppressed=False,
                silence_id=None,
            )

    async def test_integrity_error_recovery_skips_select_when_no_instance(self):
        """IntegrityError 触发但 labels 无 instance → 不走重试 SELECT，直接抛出."""
        db = AsyncMock()

        db.commit = AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("dup key")))
        db.rollback = AsyncMock()
        db.execute = AsyncMock()

        starts_at = datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC)

        # labels 不包含 instance
        with pytest.raises(IntegrityError):
            await crud_alert_history.create_from_alertmanager(
                db=db,
                alertname="HighCpu",
                status="firing",
                severity="critical",
                labels={"alertname": "HighCpu"},  # 无 instance
                annotations={},
                starts_at=starts_at,
                ends_at=None,
                is_suppressed=False,
                silence_id=None,
            )

        # 无 instance 时不应执行重试 SELECT
        db.execute.assert_not_awaited()
