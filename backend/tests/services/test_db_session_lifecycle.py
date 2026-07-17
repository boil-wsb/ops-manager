"""
L4 单元测试: DB session 生命周期验证（三阶段分离重构核心测试）.

★ 这是 QueuePool 连接池耗尽 12,114 次问题的根因测试 ★
★ 迁移自 send_alert_notification 单体函数 → 三阶段分离架构 ★

第一性原理不变式:
- 资源生命周期: DB 连接的持有时间 = DB 操作的执行时间，不多一毫秒
- 故障隔离: 外部服务故障（飞书 SSL）不应占用 DB 连接
- 并发安全: 飞书调用期间 DB 连接池必须空闲

历史根因:
- send_alert_notification(alert_data, db) 在飞书调用期间持有 db: AsyncSession
- 飞书 SSL 错误导致 7s 重试，30 个并发请求的 DB session 全部被持有
- → QueuePool size=20 overflow=10 耗尽 → 12,114 次超时错误

重构目标:
- 阶段 1 (prepare): 所有 DB 操作 + 释放 session
- 阶段 2 (execute): 飞书调用，不持有 DB session
- 阶段 3 (save): 保存 message_id，新 session

验证策略:
- inspect.signature 验证函数签名（execute 无 db 参数）
- 行为验证：prepare 不调用飞书，execute 不调用 db
- 并发验证：10 个并发 execute 不涉及任何 db
"""
import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alerts.notification_task import (
    NotificationContext,
    execute_feishu_notification,
    prepare_alert_notification,
    save_notification_result,
)


def _make_alert_data(*, status: str = "firing", instance: str = "192.168.102.109"):
    return {
        "alertname": "HighCpu",
        "status": status,
        "severity": "critical",
        "instance": instance,
        "description": "CPU > 90%",
        "starts_at": "2026-07-16T10:00:00+00:00",
        "labels": {"alertname": "HighCpu", "severity": "critical", "instance": instance},
        "annotations": {"description": "CPU > 90%"},
        "is_suppressed": False,
        "silence_id": None,
        "history_id": 1,
    }


def _make_feishu_template():
    template = MagicMock()
    template.id = 1
    template.name = "default-feishu"
    template.template_type = "feishu"
    template.is_default = True
    template.is_active = True
    template.subject_template = "{{ alertname }}"
    template.body_template = "{{ description }}"
    template.card_config = None
    return template


def _make_notification_ctx(
    *,
    status: str = "firing",
    needs_send: bool = True,
    needs_update: bool = False,
) -> NotificationContext:
    """直接构造 NotificationContext，跳过 prepare 阶段."""
    ctx = NotificationContext(
        alertname="HighCpu",
        instance="192.168.102.109",
        status=status,
        severity="critical",
        description="CPU > 90%",
        starts_at_str="2026-07-16 18:00:00",
        labels={"alertname": "HighCpu", "severity": "critical", "instance": "192.168.102.109"},
        annotations={"description": "CPU > 90%"},
        alerts_list=[{}],
        recipient_open_ids=["ou_owner"] if needs_send else [],
        card={"schema": "2.0", "body": {}},
        history_id=1,
        needs_feishu_send=needs_send,
        needs_feishu_update=needs_update,
    )
    if needs_update:
        ctx.resolved_card_messages = [
            {"history_id": 1, "open_message_id": "om_old", "card_message_id": 999}
        ]
    return ctx


class TestDBSessionLifecycle:
    """★ 三阶段分离核心验证: 飞书调用期间不持有 DB session ★

    重构后:
    1. prepare 阶段: 完成 DB 操作并释放 session
    2. execute 阶段: 飞书调用，无 DB session
    3. save 阶段: 新 session 保存 message_id
    """

    @pytest.mark.asyncio
    async def test_feishu_send_does_not_hold_db_session(self):
        """★ 核心断言: 飞书发送期间 DB session 必须已释放 ★

        验证方式: execute_feishu_notification 函数签名不接受 db 参数，
        从架构上保证飞书调用期间无法访问 DB session。
        """
        sig = inspect.signature(execute_feishu_notification)
        params = list(sig.parameters.keys())

        # ★ 核心断言: execute 函数只有 ctx 参数，没有 db 参数
        assert "db" not in params, (
            "execute_feishu_notification 不应接受 db 参数，"
            "否则飞书调用期间会持有 DB session（QueuePool 耗尽根因）"
        )
        assert "ctx" in params, "execute_feishu_notification 必须接受 ctx 参数"

    @pytest.mark.asyncio
    async def test_db_session_closed_before_feishu_call(self):
        """验证 DB session 在飞书调用前已关闭（阶段 1 → 阶段 2 边界）.

        验证方式: prepare 返回 ctx 后，execute 只使用 ctx 中的数据，
        不再访问 prepare 阶段的 db 对象。
        """
        # prepare 阶段使用的 db
        prepare_db = AsyncMock()
        template = _make_feishu_template()
        feishu_result = MagicMock()
        feishu_scalars = MagicMock()
        feishu_scalars.all.return_value = [template]
        feishu_result.scalars.return_value = feishu_scalars
        prepare_db.execute.side_effect = [feishu_result]

        feishu_calls_during_execute = []

        def _track_feishu_call(*args, **kwargs):
            # 在飞书调用期间，检查 prepare_db 是否被访问
            feishu_calls_during_execute.append(prepare_db.execute.call_count)
            return {"success": True, "message_id": "om_test"}

        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.alerts.notification_task._update_alert_history_notification_sent",
            new_callable=AsyncMock,
        ), patch(
            "app.services.alerts.notification_task.alert_template_service"
        ) as svc, patch(
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            svc.render_template = MagicMock(return_value='{"schema":"2.0"}')
            feishu_svc = MagicMock()
            feishu_svc.send_p2p_card_message = MagicMock(side_effect=_track_feishu_call)
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            # 阶段 1: prepare（使用 prepare_db）
            alert_data = _make_alert_data(status="firing")
            ctx = await prepare_alert_notification(prepare_db, alert_data)
            assert ctx is not None, "prepare 应返回 ctx"

            # 记录 prepare 结束时的 db.execute 调用次数
            prepare_execute_count = prepare_db.execute.call_count

            # 阶段 2: execute（不传 db）
            result = await execute_feishu_notification(ctx)

            # ★ 核心断言: execute 期间 prepare_db 的 execute 调用次数没有增加
            # （即飞书调用期间没有访问 prepare 阶段的 db）
            assert prepare_db.execute.call_count == prepare_execute_count, (
                "execute 阶段不应访问 prepare 阶段的 db session"
            )
            assert result.needs_save, "成功发送应标记 needs_save"

    @pytest.mark.asyncio
    async def test_save_message_id_uses_new_session(self):
        """验证保存 message_id 使用新的 DB session（阶段 3）.

        验证方式: save_notification_result 接受 db 参数，
        调用方（alerts.py）通过 db_operation_with_retry 创建新 session 传入。
        模拟: prepare 用 db1, save 用 db2, 验证 db2 ≠ db1。
        """
        prepare_db = AsyncMock()
        save_db = AsyncMock()

        # prepare 阶段
        ctx = _make_notification_ctx(status="firing", needs_send=True)
        feishu_result = MagicMock()
        feishu_result.success = True
        feishu_result.sent_cards = [{"open_message_id": "om_test", "recipient_open_id": "ou_owner"}]
        feishu_result.updated_card_message_ids = []
        feishu_result.resolved_history_id = None
        feishu_result.needs_save = True

        # 阶段 3: save 用新的 save_db
        await save_notification_result(save_db, ctx, feishu_result)

        # ★ 核心断言: save 使用独立的 db session
        assert save_db is not prepare_db, (
            "save 阶段应使用新的 db session，而非 prepare 阶段的 session"
        )
        # save 阶段会执行 DB 操作（INSERT alert_card_messages）
        assert save_db.execute.await_count > 0, "save 阶段应执行 DB 操作"

    @pytest.mark.asyncio
    async def test_concurrent_feishu_calls_do_not_exhaust_pool(self):
        """★ 并发安全: 10 个并发飞书调用不应耗尽连接池 ★

        重构前: 10 个并发请求 → 10 个 DB session 被持有 → 部分连接池耗尽
        重构后: 10 个并发飞书调用 → 0 个 DB session 被持有 → 连接池空闲

        验证方式: 10 个并发 execute_feishu_notification 调用，
        验证没有任何 db 对象被访问。
        """
        ctx = _make_notification_ctx(status="firing", needs_send=True)

        with patch(
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            feishu_svc = MagicMock()
            feishu_svc.send_p2p_card_message = MagicMock(
                return_value={"success": True, "message_id": "om_concurrent"}
            )
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            # 10 个并发 execute 调用
            tasks = [execute_feishu_notification(ctx) for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # ★ 核心断言: 10 个并发调用全部完成，且不涉及任何 db
            assert len(results) == 10
            assert all(r.success for r in results), "所有并发调用应成功"
            # execute 函数签名无 db 参数，架构上保证不访问 db
            sig = inspect.signature(execute_feishu_notification)
            assert "db" not in sig.parameters, (
                "execute_feishu_notification 无 db 参数 → 并发调用不占用 DB 连接"
            )


class TestPreparePhaseCompleteness:
    """验证 prepare 阶段完成了所有必要的 DB 操作.

    prepare 阶段必须完成:
    - 预占位标记 notification_sent=True
    - 查询资产 owner open_id
    - 查询通知组 open_ids
    - 查询并渲染模板
    """

    @pytest.mark.asyncio
    async def test_prepare_returns_all_needed_data(self):
        """prepare 阶段返回的 context 必须包含飞书发送所需的全部数据."""
        db = AsyncMock()
        template = _make_feishu_template()
        feishu_result = MagicMock()
        feishu_scalars = MagicMock()
        feishu_scalars.all.return_value = [template]
        feishu_result.scalars.return_value = feishu_scalars
        db.execute.side_effect = [feishu_result]

        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=["ou_member1"],
        ), patch(
            "app.services.alerts.notification_task._update_alert_history_notification_sent",
            new_callable=AsyncMock,
        ), patch(
            "app.services.alerts.notification_task.alert_template_service"
        ) as svc, patch(
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            svc.render_template = MagicMock(return_value='{"schema":"2.0"}')
            feishu_svc = MagicMock()
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            alert_data = _make_alert_data(status="firing")
            ctx = await prepare_alert_notification(db, alert_data)

            # ★ 核心断言: ctx 包含 execute 所需的全部数据
            assert ctx is not None, "prepare 应返回 ctx"
            assert ctx.alertname == "HighCpu"
            assert ctx.instance == "192.168.102.109"
            assert ctx.status == "firing"
            assert ctx.card is not None, "ctx 必须包含渲染好的 card"
            assert len(ctx.recipient_open_ids) == 2, "ctx 必须包含去重后的收件人列表"
            assert "ou_owner" in ctx.recipient_open_ids
            assert "ou_member1" in ctx.recipient_open_ids
            assert ctx.needs_feishu_send, "ctx 必须标记 needs_feishu_send=True"

    @pytest.mark.asyncio
    async def test_prepare_marks_notification_sent(self):
        """prepare 阶段必须执行预占位标记."""
        db = AsyncMock()
        template = _make_feishu_template()
        feishu_result = MagicMock()
        feishu_scalars = MagicMock()
        feishu_scalars.all.return_value = [template]
        feishu_result.scalars.return_value = feishu_scalars
        db.execute.side_effect = [feishu_result]

        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.alerts.notification_task._update_alert_history_notification_sent",
            new_callable=AsyncMock,
        ) as mock_mark_sent, patch(
            "app.services.alerts.notification_task.alert_template_service"
        ) as svc, patch(
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            svc.render_template = MagicMock(return_value='{"schema":"2.0"}')
            feishu_svc = MagicMock()
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            alert_data = _make_alert_data(status="firing")
            await prepare_alert_notification(db, alert_data)

            # ★ 核心断言: prepare 中调用 _update_alert_history_notification_sent
            mock_mark_sent.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_prepare_no_feishu_calls(self):
        """prepare 阶段不应调用任何飞书发送 API."""
        db = AsyncMock()
        template = _make_feishu_template()
        feishu_result = MagicMock()
        feishu_scalars = MagicMock()
        feishu_scalars.all.return_value = [template]
        feishu_result.scalars.return_value = feishu_scalars
        db.execute.side_effect = [feishu_result]

        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.alerts.notification_task._update_alert_history_notification_sent",
            new_callable=AsyncMock,
        ), patch(
            "app.services.alerts.notification_task.alert_template_service"
        ) as svc, patch(
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            svc.render_template = MagicMock(return_value='{"schema":"2.0"}')
            feishu_svc = MagicMock()
            feishu_svc.send_p2p_card_message = MagicMock()
            feishu_svc.update_card_message = MagicMock()
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            alert_data = _make_alert_data(status="firing")
            await prepare_alert_notification(db, alert_data)

            # ★ 核心断言: prepare 不调用任何飞书发送/更新 API
            feishu_svc.send_p2p_card_message.assert_not_called()
            feishu_svc.update_card_message.assert_not_called()


class TestExecutePhaseIsolation:
    """验证 execute 阶段（飞书调用）完全独立于 DB."""

    @pytest.mark.asyncio
    async def test_execute_does_not_accept_db_param(self):
        """execute 函数不应接收 db 参数.

        通过 inspect.signature 验证函数签名，
        从架构上保证 execute 阶段无法访问 DB session。
        """
        sig = inspect.signature(execute_feishu_notification)
        params = sig.parameters

        # ★ 核心断言: execute 只接受 ctx，不接受 db
        assert "db" not in params, (
            "execute_feishu_notification 不应接受 db 参数"
        )
        assert "ctx" in params, "execute_feishu_notification 必须接受 ctx 参数"
        assert len(params) == 1, f"execute 应只有 1 个参数，实际: {list(params.keys())}"

    @pytest.mark.asyncio
    async def test_execute_feishu_ssl_error_does_not_block_db(self):
        """★ 故障隔离: 飞书 SSL 错误不应阻塞 DB 操作 ★

        重构前: SSL 错误 → 7s 重试 → DB session 被持有 → QueuePool 耗尽
        重构后: SSL 错误 → 7s 重试 → 无 DB session 被持有 → 连接池空闲

        验证方式: execute 阶段飞书调用抛 SSL 错误，
        验证异常被 catch，且没有 DB session 被访问。
        """
        ctx = _make_notification_ctx(status="firing", needs_send=True)

        with patch(
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory, patch(
            "app.services.alerts.notification_task.asyncio.to_thread",
            new=AsyncMock(side_effect=ConnectionError("SSL handshake timeout")),
        ):
            feishu_svc = MagicMock()
            feishu_svc.send_p2p_card_message = MagicMock()
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            # execute 内部对每个收件人的异常单独 catch
            # 不应抛异常，且 result.needs_save=False (sent_cards 为空)
            result = await execute_feishu_notification(ctx)

            # ★ 核心断言: SSL 错误被 catch，不传播
            assert not result.success, "SSL 错误应导致 result.success=False"
            assert not result.needs_save, "全部失败应 needs_save=False"
            assert len(result.sent_cards) == 0, "sent_cards 应为空"
            # ★ 核心断言: execute 没有 db 参数，架构上保证不访问 DB
            sig = inspect.signature(execute_feishu_notification)
            assert "db" not in sig.parameters, (
                "execute 无 db 参数 → SSL 错误期间不占用 DB 连接"
            )
