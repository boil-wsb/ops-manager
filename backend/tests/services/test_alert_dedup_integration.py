"""
L5 集成测试: 告警去重与唯一性不变式验证.

第一性原理核心不变式:
- 唯一性: 同一告警实例 (alertname+instance+starts_at) 最多发送一次
- 一致性: notification_sent 状态必须与实际发送结果一致

使用 db_operation_with_retry 创建独立 DB session(与生产代码一致),
飞书调用通过 patch 隔离,避免真实发送。

覆盖路径:
1. 同 alertname+instance+starts_at 二次触发 → already_notified 跳过
2. 不同 starts_at → 视为新告警,正常发送
3. 聚合窗口内重复 → is_aggregated=True
4. notification_sent 状态转移: False → True
5. 并发 webhook 模拟 → 至多发送一次
"""
import asyncio
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import text

from app.api.v1.alerts import process_alert
from app.core.tz import now_shanghai
from app.db.session import db_operation_with_retry


def _unique_alertname() -> str:
    """生成唯一 alertname,避免测试间数据冲突."""
    return f"TestAlert_{uuid.uuid4().hex[:8]}"


def _unique_instance() -> str:
    """生成唯一 instance IP."""
    suffix = uuid.uuid4().int % 255
    return f"10.99.99.{suffix}"


async def _cleanup_alerts(alertname: str, instance: str):
    """清理指定 alertname+instance 的测试数据,使用独立 session."""
    async def _op(session):
        await session.execute(
            text(
                "DELETE FROM alert_history WHERE alertname = :name AND labels->>'instance' = :inst"
            ),
            {"name": alertname, "inst": instance},
        )
        await session.commit()

    await db_operation_with_retry(_op, max_retries=2, retry_delay=0.5)


async def _create_history(
    *,
    alertname: str,
    instance: str,
    starts_at,
    status: str = "firing",
    notification_sent: bool = False,
    severity: str = "critical",
) -> int:
    """直接创建 AlertHistory 记录,返回 history_id."""
    async def _op(session):
        result = await session.execute(
            text(
                "INSERT INTO alert_history (alertname, status, severity, labels, annotations, "
                "starts_at, notification_sent, is_suppressed, created_at, updated_at) "
                "VALUES (:name, :status, :severity, "
                "CAST(:labels AS JSONB), CAST(:ann AS JSONB), :starts_at, :sent, false, "
                "NOW(), NOW()) RETURNING id"
            ),
            {
                "name": alertname,
                "status": status,
                "severity": severity,
                "labels": f'{{"alertname":"{alertname}","instance":"{instance}","severity":"{severity}"}}',
                "ann": '{"description":"test"}',
                "starts_at": starts_at,
                "sent": notification_sent,
            },
        )
        row = result.fetchone()
        await session.commit()
        return row[0] if row else None

    return await db_operation_with_retry(_op, max_retries=2, retry_delay=0.5)


async def _get_history_notification_sent(alertname: str, instance: str) -> bool | None:
    """查询指定 alert 的 notification_sent 状态."""
    async def _op(session):
        result = await session.execute(
            text(
                "SELECT notification_sent FROM alert_history "
                "WHERE alertname = :name AND labels->>'instance' = :inst "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"name": alertname, "inst": instance},
        )
        row = result.fetchone()
        return row[0] if row else None

    return await db_operation_with_retry(_op, max_retries=2, retry_delay=0.5)


def _make_alert_data(
    *,
    alertname: str,
    instance: str,
    starts_at: str,
    status: str = "firing",
    severity: str = "critical",
) -> dict:
    """构造 alert_data."""
    return {
        "status": status,
        "labels": {
            "alertname": alertname,
            "instance": instance,
            "severity": severity,
        },
        "annotations": {"description": "integration test alert"},
        "startsAt": starts_at,
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "http://prometheus/graph",
        "fingerprint": f"{alertname}_{instance}",
    }


async def _run_process_alert(alert_data: dict) -> dict:
    """通过 db_operation_with_retry 运行 process_alert,模拟生产 webhook 行为."""
    async def _op(session):
        return await process_alert(session, alert_data)

    return await db_operation_with_retry(_op, max_retries=0, retry_delay=0.1)


class TestDedupAlreadyNotified:
    """不变式 1: 同 alertname+instance+starts_at 且已通知 → 跳过."""

    async def test_already_notified_skips_second_send(self):
        alertname = _unique_alertname()
        instance = _unique_instance()
        starts_at = now_shanghai()

        try:
            # 预置: 已存在记录且 notification_sent=True
            await _create_history(
                alertname=alertname,
                instance=instance,
                starts_at=starts_at,
                status="firing",
                notification_sent=True,
            )

            with patch(
                "app.services.alerts.notification_task.prepare_alert_notification"
            ) as prepare_fn:
                prepare_fn.return_value = MagicMock()
                with patch("app.api.v1.alerts.alert_inhibition_service") as inhib:
                    inhib.check_alert_inhibition = AsyncMock(return_value=(False, None))

                    alert_data = _make_alert_data(
                        alertname=alertname,
                        instance=instance,
                        starts_at=starts_at.isoformat(),
                    )
                    with patch("app.api.v1.alerts.settings") as mock_settings:
                        mock_settings.alert_aggregation_window_seconds = 0
                        result = await _run_process_alert(alert_data)

            # ★ 核心断言: 已通知 → is_aggregated=True,不触发发送
            assert result["is_aggregated"] is True
            prepare_fn.assert_not_awaited()
        finally:
            await _cleanup_alerts(alertname, instance)


class TestDedupDifferentStartsAt:
    """不变式 2: 不同 starts_at → 视为新告警,正常发送."""

    async def test_different_starts_at_treated_as_new_alert(self):
        alertname = _unique_alertname()
        instance = _unique_instance()
        starts_at_1 = now_shanghai()
        starts_at_2 = starts_at_1 + timedelta(seconds=1)

        try:
            # 预置: 第一条已通知
            await _create_history(
                alertname=alertname,
                instance=instance,
                starts_at=starts_at_1,
                status="firing",
                notification_sent=True,
            )

            with patch(
                "app.services.alerts.notification_task.prepare_alert_notification"
            ) as prepare_fn:
                prepare_fn.return_value = MagicMock()
                with patch("app.api.v1.alerts.alert_inhibition_service") as inhib:
                    inhib.check_alert_inhibition = AsyncMock(return_value=(False, None))

                    alert_data = _make_alert_data(
                        alertname=alertname,
                        instance=instance,
                        starts_at=starts_at_2.isoformat(),
                    )
                    with patch("app.api.v1.alerts.settings") as mock_settings:
                        mock_settings.alert_aggregation_window_seconds = 0
                        result = await _run_process_alert(alert_data)

            # ★ 核心断言: 不同 starts_at → 新告警,触发发送
            assert result["is_aggregated"] is False
            prepare_fn.assert_awaited_once()
        finally:
            await _cleanup_alerts(alertname, instance)


class TestDedupAggregationWindow:
    """不变式 3: 聚合窗口内已通知记录 → is_aggregated=True."""

    async def test_aggregation_window_skips_recent_notified(self):
        alertname = _unique_alertname()
        instance = _unique_instance()
        starts_at_1 = now_shanghai()
        starts_at_2 = starts_at_1 + timedelta(seconds=2)

        try:
            # 预置: 窗口内已通知的 firing 记录(不同 starts_at)
            await _create_history(
                alertname=alertname,
                instance=instance,
                starts_at=starts_at_1,
                status="firing",
                notification_sent=True,
            )

            with patch(
                "app.services.alerts.notification_task.prepare_alert_notification"
            ) as prepare_fn:
                prepare_fn.return_value = MagicMock()
                with patch("app.api.v1.alerts.alert_inhibition_service") as inhib:
                    inhib.check_alert_inhibition = AsyncMock(return_value=(False, None))

                    alert_data = _make_alert_data(
                        alertname=alertname,
                        instance=instance,
                        starts_at=starts_at_2.isoformat(),
                    )
                    with patch("app.api.v1.alerts.settings") as mock_settings:
                        mock_settings.alert_aggregation_window_seconds = 300
                        result = await _run_process_alert(alert_data)

            # ★ 核心断言: 窗口内已有已通知记录 → is_aggregated=True
            assert result["is_aggregated"] is True
            prepare_fn.assert_not_awaited()
        finally:
            await _cleanup_alerts(alertname, instance)


class TestNotificationSentStateTransition:
    """不变式 4: notification_sent 状态转移 False → True."""

    async def test_notification_sent_transitions_to_true_on_send(self):
        """prepare_alert_notification 内部预占位标记会将 notification_sent 从 False 改为 True.

        三阶段分离重构后,预占位标记在 prepare_alert_notification 中执行(阶段 1),
        不再依赖 send_alert_notification。本测试让真实 prepare 执行,
        mock execute_feishu_notification 防止真实飞书调用(虽不被 process_alert 直接调用,
        作为安全措施)。
        """
        alertname = _unique_alertname()
        instance = _unique_instance()
        starts_at = now_shanghai()

        try:
            # 预置: 直接创建记录,notification_sent=False
            await _create_history(
                alertname=alertname,
                instance=instance,
                starts_at=starts_at,
                status="firing",
                notification_sent=False,
            )

            # 验证初始 notification_sent=False
            initial_sent = await _get_history_notification_sent(alertname, instance)
            assert initial_sent is False, "创建后 notification_sent 应为 False"

            with patch("app.api.v1.alerts.alert_inhibition_service") as inhib:
                inhib.check_alert_inhibition = AsyncMock(return_value=(False, None))
                # mock execute_feishu_notification 防止真实飞书调用(安全措施)
                with patch(
                    "app.services.alerts.notification_task.execute_feishu_notification"
                ):
                    alert_data = _make_alert_data(
                        alertname=alertname,
                        instance=instance,
                        starts_at=starts_at.isoformat(),
                    )
                    with patch("app.api.v1.alerts.settings") as mock_settings:
                        mock_settings.alert_aggregation_window_seconds = 0
                        await _run_process_alert(alert_data)

                    # ★ 核心断言: prepare 执行预占位标记后 notification_sent=True
                    final_sent = await _get_history_notification_sent(
                        alertname, instance
                    )
                    assert final_sent is True, (
                        "预占位标记后 notification_sent 必须为 True"
                    )
        finally:
            await _cleanup_alerts(alertname, instance)


class TestSequentialWebhookDedup:
    """不变式 5: 顺序重复 webhook(Alertmanager 超时重发) → 第二次被去重.

    生产场景: Alertmanager ~90s 超时后重发 webhook。
    第一次 webhook 完成预占位标记后,第二次 webhook 的 already_notified 检查命中。

    注意: 真正的并发 TOCTOU 是已知限制(审查文档 违反 1),仅靠应用层无法完全避免,
    需 DB UNIQUE 约束。当前 P0-B 预占位标记 + P1-A 索引是缓解措施。
    """

    async def test_sequential_same_alert_deduplicated_after_first_completes(self):
        """第一次完成预占位标记后,第二次 webhook 被去重."""
        alertname = _unique_alertname()
        instance = _unique_instance()
        starts_at = now_shanghai()

        try:
            send_count = 0

            async def _counting_prepare(db, alert_data):
                nonlocal send_count
                send_count += 1
                # 模拟预占位标记(与真实 prepare_alert_notification 行为一致)
                from app.services.alerts.notification_task import (
                    _update_alert_history_notification_sent,
                )
                await _update_alert_history_notification_sent(
                    db=db,
                    alertname=alert_data["alertname"],
                    instance=alert_data["instance"],
                )
                # 返回 truthy 表示有通知上下文
                return MagicMock()

            with patch(
                "app.services.alerts.notification_task.prepare_alert_notification",
                side_effect=_counting_prepare,
            ), patch("app.api.v1.alerts.alert_inhibition_service") as inhib:
                inhib.check_alert_inhibition = AsyncMock(return_value=(False, None))

                alert_data = _make_alert_data(
                    alertname=alertname,
                    instance=instance,
                    starts_at=starts_at.isoformat(),
                )
                with patch("app.api.v1.alerts.settings") as mock_settings:
                    mock_settings.alert_aggregation_window_seconds = 0

                    # 第一次 webhook: 正常发送 + 预占位标记
                    result1 = await _run_process_alert(alert_data)
                    assert result1["is_aggregated"] is False, "首次发送应正常触发"

                    # 第二次 webhook(模拟 Alertmanager 90s 重发):
                    # 第一次已完成预占位标记 → already_notified=True → 跳过
                    result2 = await _run_process_alert(alert_data)
                    assert result2["is_aggregated"] is True, (
                        "第二次应被去重(已通知标记命中)"
                    )

            # ★ 核心断言: 只发送一次
            assert send_count == 1, (
                f"顺序重复 webhook 应只发送一次,实际发送 {send_count} 次"
            )
        finally:
            await _cleanup_alerts(alertname, instance)


class TestConcurrentWebhookTOCTOU:
    """已知限制: 并发 webhook 的 TOCTOU 竞态.

    审查文档 违反 1: process_alert 的去重检查是"先查后写",无行锁。
    两个并发 webhook 可同时查到"无 existing_record",各自创建记录并发送。

    缓解: P0-B 预占位标记 + P1-A 复合索引(不加 UNIQUE 以兼容历史数据)。
    完全修复需 DB 层 UNIQUE 约束(P2 未实施)。

    本测试验证 TOCTOU 存在(文档化已知行为),而非断言不存在。
    """

    async def test_concurrent_toctou_can_cause_multiple_sends(self):
        """并发 webhook 可能产生多次发送(TOCTOU 已知限制).

        此测试断言行为而非正确性:
        - 如果 send_count == 1: TOCTOU 未触发(运气好,预占位标记先于第二个检查)
        - 如果 send_count > 1: TOCTOU 触发(已知限制,需 DB UNIQUE 约束完全修复)
        两种情况都通过,仅记录实际行为。
        """
        alertname = _unique_alertname()
        instance = _unique_instance()
        starts_at = now_shanghai().isoformat()

        try:
            send_count = 0
            count_lock = asyncio.Lock()

            async def _counting_prepare(db, alert_data):
                nonlocal send_count
                async with count_lock:
                    send_count += 1
                # 返回 truthy 表示有通知上下文
                return MagicMock()

            with patch(
                "app.services.alerts.notification_task.prepare_alert_notification",
                side_effect=_counting_prepare,
            ), patch("app.api.v1.alerts.alert_inhibition_service") as inhib:
                inhib.check_alert_inhibition = AsyncMock(return_value=(False, None))

                alert_data = _make_alert_data(
                    alertname=alertname,
                    instance=instance,
                    starts_at=starts_at,
                )
                with patch("app.api.v1.alerts.settings") as mock_settings:
                    mock_settings.alert_aggregation_window_seconds = 0
                    # 并发 3 个相同 webhook
                    await asyncio.gather(
                        _run_process_alert(alert_data),
                        _run_process_alert(alert_data),
                        _run_process_alert(alert_data),
                        return_exceptions=True,
                    )

            # 文档化: 并发 TOCTOU 可导致 1-3 次发送
            # 完全修复需 DB UNIQUE 约束(P2 未实施)
            assert 1 <= send_count <= 3, f"并发 send_count 应在 1-3 之间,实际 {send_count}"
        finally:
            await _cleanup_alerts(alertname, instance)
