"""
L2 单元测试: process_alert 所有分支覆盖.

第一性原理覆盖的不变式:
- 可达性: 未抑制未聚合的告警必须触发 prepare_alert_notification
- 唯一性: already_notified=True 时跳过通知
- 一致性: DB 状态转移与决策点一致

覆盖路径:
1. firing + 新告警 → 创建历史记录 + 触发 prepare_alert_notification
2. firing + 已存在记录 + 已通知 → 跳过通知 (already_notified)
3. firing + 已存在记录 + 未通知 → 更新记录 + 触发 prepare_alert_notification
4. firing + 聚合窗口命中 → 跳过通知 (is_aggregated)
5. resolved + 批量更新老 firing 记录
6. suppressed → 状态置 SUPPRESSED + 跳过通知
7. 抑制检查异常 → 降级为 is_suppressed=False 继续流程
8. 历史记录创建异常 → 抛出异常
9. 无 instance → 不查已存在记录,直接创建

三阶段分离重构:
- 重构前: process_alert 调用 send_alert_notification(alert_data, db)
- 重构后: process_alert 调用 prepare_alert_notification(db, alert_data) 返回 NotificationContext 或 None
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.alerts import parse_alertmanager_datetime, process_alert
from app.models.alert import AlertHistory, AlertHistoryStatus


def _make_alert_data(
    *,
    alertname: str = "HighCpu",
    status: str = "firing",
    severity: str = "critical",
    instance: str = "192.168.1.10",
    starts_at: str = "2026-07-16T10:00:00Z",
    ends_at: str | None = None,
    labels: dict | None = None,
) -> dict:
    """构造 Alertmanager 单条 alert dict."""
    base_labels = {"alertname": alertname, "severity": severity}
    if instance:
        base_labels["instance"] = instance
    if labels:
        base_labels.update(labels)
    return {
        "status": status,
        "labels": base_labels,
        "annotations": {"description": "test alert"},
        "startsAt": starts_at,
        "endsAt": ends_at or "0001-01-01T00:00:00Z",
        "generatorURL": "http://prometheus/graph",
        "fingerprint": "abc123",
    }


def _make_history(
    *, id: int = 1, notification_sent: bool = False, status: str = "firing"
) -> AlertHistory:
    """构造 AlertHistory 实例."""
    return AlertHistory(
        id=id,
        alertname="HighCpu",
        status=status,
        severity="critical",
        labels={"instance": "192.168.1.10"},
        annotations={},
        starts_at=datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC),
        notification_sent=notification_sent,
    )


@pytest.fixture
def mock_db():
    """Mock AsyncSession,提供链式 execute/commit/refresh."""
    db = AsyncMock()
    # execute 返回 MagicMock,便于配置 scalar_one_or_none / scalars / fetchone
    db.execute.return_value = MagicMock()
    return db


@pytest.fixture
def patched_inhibition():
    """patch 抑制检查服务."""
    with patch("app.api.v1.alerts.alert_inhibition_service") as svc:
        svc.check_alert_inhibition = AsyncMock(return_value=(False, None))
        yield svc


@pytest.fixture
def patched_send_notification():
    """patch prepare_alert_notification 防止真实发送 (三阶段分离阶段 1)."""
    with patch(
        "app.services.alerts.notification_task.prepare_alert_notification",
        new=AsyncMock(),
    ) as fn:
        yield fn


@pytest.fixture
def patched_crud_create():
    """patch crud_alert_history.create_from_alertmanager."""
    with patch("app.api.v1.alerts.crud_alert_history") as crud:
        crud.create_from_alertmanager = AsyncMock()
        yield crud


class TestProcessAlertFiringNewAlert:
    """场景 1: firing 新告警,创建历史 + 触发通知."""

    async def test_firing_new_alert_creates_history_and_sends_notification(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # 三阶段分离: prepare_alert_notification 返回 truthy 表示有通知上下文
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=MagicMock()),
        ) as prepare_fn:
            patched_crud_create.create_from_alertmanager.return_value = _make_history(id=100)

            # existing_query 返回 None(无已存在记录)
            existing_result = MagicMock()
            existing_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = existing_result

            alert_data = _make_alert_data()
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 0
                result = await process_alert(mock_db, alert_data)

            assert result["history_id"] == 100
            assert result["status"] == AlertHistoryStatus.FIRING.value
            assert result["is_suppressed"] is False
            assert result["is_aggregated"] is False
            patched_crud_create.create_from_alertmanager.assert_awaited_once()
            prepare_fn.assert_awaited_once()
            # 三阶段分离: notification_ctx 应为 truthy
            assert result["notification_ctx"] is not None


class TestProcessAlertAlreadyNotified:
    """场景 2: firing 已存在记录且已通知 → 跳过通知 (唯一性不变式)."""

    async def test_firing_already_notified_skips_notification(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # already_notified 分支不会调用 prepare,但仍 mock 以防真实调用
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=None),
        ) as prepare_fn:
            # 已存在记录且 notification_sent=True
            existing_history = _make_history(id=200, notification_sent=True)
            existing_result = MagicMock()
            existing_result.scalar_one_or_none.return_value = existing_history
            mock_db.execute.return_value = existing_result

            alert_data = _make_alert_data()
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 300
                result = await process_alert(mock_db, alert_data)

            assert result["is_aggregated"] is True
            prepare_fn.assert_not_awaited()
            patched_crud_create.create_from_alertmanager.assert_not_called()
            assert result["notification_ctx"] is None


class TestProcessAlertExistingNotNotified:
    """场景 3: firing 已存在记录但未通知 → 更新记录 + 触发通知."""

    async def test_firing_existing_not_notified_updates_and_sends(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # 三阶段分离: prepare_alert_notification 返回 truthy 表示有通知上下文
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=MagicMock()),
        ) as prepare_fn:
            existing_history = _make_history(id=300, notification_sent=False)
            existing_result = MagicMock()
            existing_result.scalar_one_or_none.return_value = existing_history

            # 聚合查询返回 0
            agg_result = MagicMock()
            agg_result.scalar.return_value = 0

            mock_db.execute.side_effect = [existing_result, agg_result]

            alert_data = _make_alert_data()
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 300
                result = await process_alert(mock_db, alert_data)

            assert result["is_aggregated"] is False
            assert result["history_id"] == 300
            prepare_fn.assert_awaited_once()
            assert result["notification_ctx"] is not None
            # 更新已存在记录时调用 commit
            assert mock_db.commit.await_count >= 1
            patched_crud_create.create_from_alertmanager.assert_not_called()


class TestProcessAlertAggregationWindow:
    """场景 4: 聚合窗口命中 → 跳过通知."""

    async def test_aggregation_window_hit_skips_notification(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # 聚合命中分支不会调用 prepare,但仍 mock 以防真实调用
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=None),
        ) as prepare_fn:
            # 无已存在记录
            existing_result = MagicMock()
            existing_result.scalar_one_or_none.return_value = None

            # 聚合查询返回 1(窗口内已有已通知记录)
            agg_result = MagicMock()
            agg_result.scalar.return_value = 1

            mock_db.execute.side_effect = [existing_result, agg_result]

            patched_crud_create.create_from_alertmanager.return_value = _make_history(id=400)

            alert_data = _make_alert_data()
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 300
                result = await process_alert(mock_db, alert_data)

            assert result["is_aggregated"] is True
            prepare_fn.assert_not_awaited()
            assert result["notification_ctx"] is None


class TestProcessAlertResolvedBatchUpdate:
    """场景 5: resolved 时批量更新老 firing 记录."""

    async def test_resolved_batch_updates_pending_firing_alerts(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # resolved 场景: prepare 被调用但返回 None (不走 firing 发送路径)
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=None),
        ) as prepare_fn:
            # 批量查询返回 2 条 pending firing
            pending1 = _make_history(id=500, status="firing")
            pending2 = _make_history(id=501, status="firing")
            pending_result = MagicMock()
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = [pending1, pending2]
            pending_result.scalars.return_value = scalars_mock

            # 已存在记录查询(resolved 不进入该分支,但 execute 会被批量查询调用)
            mock_db.execute.return_value = pending_result

            alert_data = _make_alert_data(status="resolved", ends_at="2026-07-16T11:00:00Z")
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 0
                result = await process_alert(mock_db, alert_data)

            assert result["status"] == AlertHistoryStatus.RESOLVED.value
            # 批量更新调用 commit
            mock_db.commit.assert_awaited()
            # 两条 pending 状态都改为 resolved
            assert pending1.status == AlertHistoryStatus.RESOLVED.value
            assert pending2.status == AlertHistoryStatus.RESOLVED.value
            assert pending1.ends_at is not None
            assert pending2.ends_at is not None
            # resolved 场景: prepare 被调用但返回 None (不走 firing 发送路径)
            prepare_fn.assert_awaited_once()
            assert result["notification_ctx"] is None


class TestProcessAlertResolvedStartsAtNone:
    """场景 5b: ND-2 修复 - resolved 时 startsAt=None 仍走批量更新 (fallback now_shanghai).

    不变式: starts_at=None 时不应跳过批量 resolve 块，否则旧 firing 记录会永久残留。
    """

    async def test_resolved_with_starts_at_none_still_batch_updates(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # resolved 场景: prepare 返回 None
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=None),
        ) as prepare_fn:
            # 批量查询返回 1 条 pending firing
            pending = _make_history(id=510, status="firing")
            pending_result = MagicMock()
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = [pending]
            pending_result.scalars.return_value = scalars_mock
            mock_db.execute.return_value = pending_result

            # startsAt 缺失（None）—— ND-2 关键场景
            alert_data = _make_alert_data(
                status="resolved", starts_at=None, ends_at="2026-07-16T11:00:00Z"
            )
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 0
                with patch("app.api.v1.alerts.now_shanghai") as mock_now:
                    fallback_dt = datetime(2026, 7, 16, 10, 30, 0, tzinfo=UTC)
                    mock_now.return_value = fallback_dt
                    result = await process_alert(mock_db, alert_data)

            assert result["status"] == AlertHistoryStatus.RESOLVED.value
            # 批量更新调用 commit (ND-2 关键断言: 不应跳过批量更新块)
            mock_db.commit.assert_awaited()
            # pending 状态被改为 resolved
            assert pending.status == AlertHistoryStatus.RESOLVED.value
            assert pending.ends_at is not None
            prepare_fn.assert_awaited_once()


class TestProcessAlertSuppressed:
    """场景 6: 抑制规则命中 → 状态 SUPPRESSED + 跳过通知."""

    async def test_suppressed_alert_sets_status_and_skips_notification(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # suppressed 分支不会调用 prepare,但仍 mock 以防真实调用
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=None),
        ) as prepare_fn:
            patched_inhibition.check_alert_inhibition.return_value = (True, 999)

            existing_result = MagicMock()
            existing_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = existing_result

            patched_crud_create.create_from_alertmanager.return_value = _make_history(id=600)

            alert_data = _make_alert_data()
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 0
                result = await process_alert(mock_db, alert_data)

            assert result["is_suppressed"] is True
            assert result["status"] == AlertHistoryStatus.SUPPRESSED.value
            assert result["silence_id"] == 999
            prepare_fn.assert_not_awaited()
            assert result["notification_ctx"] is None


class TestProcessAlertInhibitionCheckException:
    """场景 7: 抑制检查异常 → 降级为 is_suppressed=False 继续流程 (容错性)."""

    async def test_inhibition_exception_degrades_to_not_suppressed(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # 三阶段分离: prepare_alert_notification 返回 truthy 表示有通知上下文
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=MagicMock()),
        ) as prepare_fn:
            patched_inhibition.check_alert_inhibition.side_effect = RuntimeError(
                "DB connection lost"
            )

            existing_result = MagicMock()
            existing_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = existing_result

            patched_crud_create.create_from_alertmanager.return_value = _make_history(id=700)

            alert_data = _make_alert_data()
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 0
                result = await process_alert(mock_db, alert_data)

            # 异常被捕获,降级为不抑制
            assert result["is_suppressed"] is False
            assert result["status"] == AlertHistoryStatus.FIRING.value
            # 仍然触发通知(可达性不变式)
            prepare_fn.assert_awaited_once()
            assert result["notification_ctx"] is not None


class TestProcessAlertHistoryCreateException:
    """场景 8: 历史记录创建异常 → 抛出异常 (不静默失败)."""

    async def test_history_create_exception_propagates(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        patched_inhibition.check_alert_inhibition.return_value = (False, None)

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = existing_result

        patched_crud_create.create_from_alertmanager.side_effect = RuntimeError(
            "IntegrityError: duplicate key"
        )

        alert_data = _make_alert_data()
        with patch("app.api.v1.alerts.settings") as mock_settings:
            mock_settings.alert_aggregation_window_seconds = 0
            with pytest.raises(RuntimeError, match="duplicate key"):
                await process_alert(mock_db, alert_data)


class TestProcessAlertNoInstance:
    """场景 9: 无 instance → 不查已存在记录,直接创建."""

    async def test_no_instance_skips_existing_check(
        self, mock_db, patched_inhibition, patched_crud_create
    ):
        # 无 instance 时 prepare 仍被调用,但内部会因 instance 为空返回 None
        with patch(
            "app.services.alerts.notification_task.prepare_alert_notification",
            new=AsyncMock(return_value=None),
        ) as prepare_fn:
            patched_crud_create.create_from_alertmanager.return_value = _make_history(id=800)

            alert_data = _make_alert_data(instance="")
            with patch("app.api.v1.alerts.settings") as mock_settings:
                mock_settings.alert_aggregation_window_seconds = 0
                result = await process_alert(mock_db, alert_data)

            assert result["history_id"] == 800
            # 无 instance 时 prepare 仍被调用,但返回 None (无收件人)
            prepare_fn.assert_awaited_once()
            assert result["notification_ctx"] is None
            # execute 不应被调用(existing_record 查询需 instance 非空)
            mock_db.execute.assert_not_awaited()


class TestParseAlertmanagerDatetime:
    """parse_alertmanager_datetime 边界覆盖(服务于流程理解)."""

    def test_none_returns_none(self):
        assert parse_alertmanager_datetime(None) is None

    def test_datetime_passthrough(self):
        dt = datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC)
        assert parse_alertmanager_datetime(dt) is dt

    def test_zero_value_returns_none(self):
        """Alertmanager '0001-01-01T00:00:00Z' 表示无结束时间."""
        assert parse_alertmanager_datetime("0001-01-01T00:00:00Z") is None

    def test_iso_with_z_suffix(self):
        result = parse_alertmanager_datetime("2026-07-16T10:00:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.month == 7
        assert result.day == 16

    def test_invalid_string_returns_none(self):
        assert parse_alertmanager_datetime("not-a-date") is None

    def test_empty_string_returns_none(self):
        assert parse_alertmanager_datetime("") is None
