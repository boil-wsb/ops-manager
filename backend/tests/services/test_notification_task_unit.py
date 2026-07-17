"""
L3 单元测试: 三阶段通知 API 全路径覆盖.

★ 这是 192.168.102.109 重复发送 bug 的根因测试文件 ★
★ 迁移自 send_alert_notification 单体函数 → 三阶段分离架构 ★

第一性原理覆盖的不变式:
- 一致性 (P0-B): notification_sent 必须在飞书发送 *前* 标记 (预占位)
- 一致性 (P0-C): else 分支(无收件人)也必须标记 notification_sent=True
- 可达性: 有收件人时必须真正调用飞书发送
- 时效性 (P1-B): 飞书调用必须通过 asyncio.to_thread 包装,不阻塞事件循环
- 架构不变式: DB session 生命周期 = DB 操作时间（三阶段分离）

三阶段 API:
- prepare_alert_notification(db, alert_data) → NotificationContext | None
- execute_feishu_notification(ctx) → FeishuResult
- save_notification_result(db, ctx, result) → None

覆盖路径:
1. firing + 有收件人 → 预占位标记 + 飞书发送 + 保存 message_id
2. firing + 无收件人 (P0-C 根因) → 必须标记 notification_sent=True
3. firing + DB 异常查负责人 (P0-A) → 仍标记 notification_sent=True
4. resolved → execute 阶段更新卡片 (不发送新卡片)
5. 预占位顺序验证 (P0-B): 标记必须在发送前 (prepare 阶段完成)
6. asyncio.to_thread 包装验证 (P1-B)
7. 无 instance → 直接返回
8. 多收件人去重 + 首个 message_id 保存
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alerts.notification_task import (
    _get_alert_notification_group_open_ids,
    _get_asset_owner_open_id,
    _update_alert_history_notification_sent,
    execute_feishu_notification,
    prepare_alert_notification,
    save_notification_result,
)


async def _run_three_stage(alert_data: dict, db) -> None:
    """运行三阶段通知流程（模拟 alerts.py 的调用顺序）.

    prepare → execute → save
    """
    ctx = await prepare_alert_notification(db, alert_data)
    if ctx is None:
        return
    result = await execute_feishu_notification(ctx)
    if result.needs_save:
        await save_notification_result(db, ctx, result)


def _make_alert_data(
    *,
    status: str = "firing",
    instance: str = "192.168.102.109",
    alertname: str = "HighCpu",
    severity: str = "critical",
) -> dict:
    """构造 alert_data."""
    return {
        "alertname": alertname,
        "status": status,
        "severity": severity,
        "instance": instance,
        "description": "CPU usage > 90%",
        "starts_at": "2026-07-16T10:00:00+00:00",
        "labels": {"alertname": alertname, "severity": severity, "instance": instance},
        "annotations": {"description": "CPU usage > 90%"},
        "is_suppressed": False,
        "silence_id": None,
        "history_id": 1,
    }


def _make_feishu_template(*, with_card_config: bool = False):
    """构造 AlertTemplate mock."""
    template = MagicMock()
    template.id = 1
    template.name = "default-feishu"
    template.template_type = "feishu"
    template.is_default = True
    template.is_active = True
    template.subject_template = "告警: {{ alertname }}"
    template.body_template = "{{ description }}"
    template.card_config = {"schema": "2.0", "body": {}} if with_card_config else None
    return template


@pytest.fixture
def mock_db():
    """Mock AsyncSession,默认返回空 templates 列表."""
    db = AsyncMock()
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result.scalars.return_value = scalars_mock
    db.execute.return_value = result
    return db


@pytest.fixture
def mock_db_with_feishu_template(mock_db):
    """Mock DB 返回一个 feishu 模板(无 card_config,走 build_alert_card).

    新架构 prepare_alert_notification 只查询 feishu 模板（1 次 execute），
    旧 send_alert_notification 查询 email + feishu（2 次）。
    """
    template = _make_feishu_template(with_card_config=False)
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [template]
    result.scalars.return_value = scalars_mock
    mock_db.execute.side_effect = [result]
    return mock_db


@pytest.fixture
def patched_template_render():
    """patch alert_template_service.render_alert_template 返回有效内容."""
    with patch(
        "app.services.alerts.notification_task.alert_template_service"
    ) as svc:
        svc.render_alert_template = AsyncMock(return_value=("告警主题", "告警正文"))
        svc.render_template = MagicMock(return_value='{"schema":"2.0","body":{}}')
        yield svc


@pytest.fixture
def patched_owner_lookup():
    """patch _get_asset_owner_open_id."""
    with patch(
        "app.services.alerts.notification_task._get_asset_owner_open_id",
        new_callable=AsyncMock,
    ) as fn:
        fn.return_value = None
        yield fn


@pytest.fixture
def patched_group_lookup():
    """patch _get_alert_notification_group_open_ids."""
    with patch(
        "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
        new_callable=AsyncMock,
    ) as fn:
        fn.return_value = []
        yield fn


@pytest.fixture
def patched_mark_sent():
    """patch _update_alert_history_notification_sent."""
    with patch(
        "app.services.alerts.notification_task._update_alert_history_notification_sent",
        new_callable=AsyncMock,
    ) as fn:
        yield fn


@pytest.fixture
def patched_save_message_id():
    """patch save_notification_result (阶段 3).

    旧 API patch _save_firing_alert_message_id，三阶段分离后
    message_id 保存逻辑移入 save_notification_result。

    注意: _run_three_stage 在测试模块内调用 save_notification_result，
    所以必须 patch 测试模块的引用，而非源模块的引用（Python mock 陷阱）。
    """
    with patch(
        "tests.services.test_notification_task_unit.save_notification_result",
        new_callable=AsyncMock,
    ) as fn:
        yield fn


@pytest.fixture
def mock_feishu_svc():
    """patch get_feishu_notification_service 返回 mock service."""
    svc = MagicMock()
    svc.send_p2p_card_message = MagicMock(return_value={"success": True, "message_id": "om_test123"})
    svc.update_card_message = MagicMock(return_value={"success": True})
    svc.build_alert_card = MagicMock(return_value={"schema": "2.0", "body": {}})
    svc.build_resolved_card = MagicMock(return_value={"schema": "2.0", "body": {}})
    with patch(
        "app.services.alerts.notification_task.get_feishu_notification_service",
        return_value=svc,
    ):
        yield svc


class TestSendAlertNoInstance:
    """场景 7: 无 instance → 直接返回,不发送."""

    async def test_no_instance_returns_early(self, mock_db):
        alert_data = _make_alert_data(instance="")

        await _run_three_stage(alert_data, mock_db)

        # execute 不应被调用(模板查询在 instance 检查之后)
        mock_db.execute.assert_not_awaited()


class TestSendAlertFiringWithRecipients:
    """场景 1: firing + 有收件人 → 预占位标记 + 飞书发送 + 保存 message_id."""

    async def test_firing_with_recipient_marks_sent_then_sends(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_owner_lookup,
        patched_group_lookup,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        """P0-B 核心验证: 标记必须在发送前."""
        patched_owner_lookup.return_value = "ou_owner_123"
        patched_group_lookup.return_value = ["ou_member_456"]

        alert_data = _make_alert_data(status="firing")

        # 用 call_order 验证标记在发送前
        call_order = []

        async def _mark_sent_side_effect(db, alertname, instance, starts_at=None):
            call_order.append("mark_sent")
            return None

        patched_mark_sent.side_effect = _mark_sent_side_effect

        async def _fake_to_thread(func, *args, **kwargs):
            call_order.append("feishu_send")
            return func(*args, **kwargs)

        with patch("app.services.alerts.notification_task.asyncio.to_thread", _fake_to_thread):
            await _run_three_stage(alert_data, mock_db_with_feishu_template)

        # ★ 核心断言: mark_sent 必须在 feishu_send 之前
        assert call_order[0] == "mark_sent", "预占位标记必须在飞书发送前执行 (P0-B)"
        assert "feishu_send" in call_order
        patched_mark_sent.assert_awaited_once()
        # 两个收件人都发送
        assert mock_feishu_svc.send_p2p_card_message.call_count == 2
        # 保存首个 message_id
        patched_save_message_id.assert_awaited_once()

    async def test_multiple_recipients_deduplicated(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        """收件人去重: asset owner 同时在通知组 → 只发送一次."""
        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_dup",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=["ou_dup", "ou_other"],
        ):
            alert_data = _make_alert_data(status="firing")

            await _run_three_stage(alert_data, mock_db_with_feishu_template)

            # ou_dup 去重,只发送给 ou_dup 和 ou_other
            assert mock_feishu_svc.send_p2p_card_message.call_count == 2
            called_ids = [
                call.kwargs.get("open_id") or call.args[0]
                for call in mock_feishu_svc.send_p2p_card_message.call_args_list
            ]
            assert "ou_dup" in called_ids
            assert "ou_other" in called_ids
            assert called_ids.count("ou_dup") == 1


class TestSendAlertNoRecipient:
    """★ 场景 2 (P0-C 根因): firing + 无收件人 → 必须标记 notification_sent=True ★

    历史根因: 旧代码 else 分支仅记日志,未调用 _update_alert_history_notification_sent,
    导致 notification_sent 永远为 False,后续 webhook 全部通过去重检查 → 17 张重复卡片。
    """

    async def test_firing_no_recipient_still_marks_sent(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_owner_lookup,
        patched_group_lookup,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        """无资产负责人 + 无通知组成员 → 仍必须标记 notification_sent=True."""
        patched_owner_lookup.return_value = None
        patched_group_lookup.return_value = []

        alert_data = _make_alert_data(status="firing")

        await _run_three_stage(alert_data, mock_db_with_feishu_template)

        # ★ 核心断言: 即使无收件人也必须标记 notification_sent=True (P0-C 修复)
        patched_mark_sent.assert_awaited_once()
        # 不应调用飞书发送
        mock_feishu_svc.send_p2p_card_message.assert_not_called()
        # 不应保存 message_id
        patched_save_message_id.assert_not_awaited()

    async def test_firing_only_notification_group_no_owner_marks_sent(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_owner_lookup,
        patched_group_lookup,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        """无资产负责人但有通知组 → 发送给通知组 + 标记."""
        patched_owner_lookup.return_value = None
        patched_group_lookup.return_value = ["ou_member_1", "ou_member_2"]

        alert_data = _make_alert_data(status="firing")

        await _run_three_stage(alert_data, mock_db_with_feishu_template)

        # 有收件人 → 走发送分支,标记在发送前
        patched_mark_sent.assert_awaited_once()
        assert mock_feishu_svc.send_p2p_card_message.call_count == 2


class TestSendAlertResolved:
    """场景 4: resolved → execute 阶段调用 update_card_message,不发送新卡片.

    三阶段架构下 resolved 路径:
    - prepare: 查询 alert_card_messages WHERE card_status='firing' → ctx.resolved_card_messages
    - execute: 调用 update_card_message（通过 asyncio.to_thread）→ result.updated_card_message_ids
    - save: 更新 alert_card_messages.card_status='resolved' + alert_history.status='resolved'
    """

    async def test_resolved_calls_update_card_message(
        self,
        mock_db,
        patched_template_render,
        patched_owner_lookup,
        patched_group_lookup,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        """resolved → execute 调用 update_card_message, 不走 firing 分支."""
        patched_owner_lookup.return_value = "ou_owner_123"
        patched_group_lookup.return_value = []

        # 构造 DB execute 返回值:
        # 1. feishu template query → [template]
        # 2. resolved SELECT alert_card_messages → rows(id, open_message_id, alert_history_id)
        template = _make_feishu_template(with_card_config=False)

        def _make_scalars_result(items):
            r = MagicMock()
            s = MagicMock()
            s.all.return_value = items
            r.scalars.return_value = s
            return r

        select_result = MagicMock()
        row = MagicMock()
        row.__getitem__ = MagicMock(side_effect=lambda i: {0: 999, 1: "om_old_msg", 2: 42}[i])
        select_result.fetchall.return_value = [row]

        mock_db.execute.side_effect = [
            _make_scalars_result([template]),  # feishu templates
            select_result,                     # resolved SELECT alert_card_messages
        ]

        alert_data = _make_alert_data(status="resolved")

        await _run_three_stage(alert_data, mock_db)

        # resolved → execute 调用 update_card_message
        mock_feishu_svc.update_card_message.assert_called_once()
        # resolved → 不走 firing 发送分支
        patched_mark_sent.assert_not_awaited()
        # resolved 成功更新 → save_notification_result 被调用以更新 card_status
        patched_save_message_id.assert_awaited_once()
        # resolved → 不调用 send_p2p_card_message
        mock_feishu_svc.send_p2p_card_message.assert_not_called()

    async def test_resolved_no_firing_card_returns_none(
        self,
        mock_db,
        patched_template_render,
        patched_owner_lookup,
        patched_group_lookup,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        """resolved 时无 firing 卡片（也无 legacy feishu_open_message_id）→ prepare 返回 None."""
        patched_owner_lookup.return_value = "ou_owner_123"
        patched_group_lookup.return_value = []

        # 构造 DB execute 返回值:
        # 1. feishu template query → [template]
        # 2. resolved SELECT alert_card_messages → 空 (fetchall=[])
        # 3. legacy fallback SELECT alert_history → 空 (fetchone=None)
        template = _make_feishu_template(with_card_config=False)

        def _make_scalars_result(items):
            r = MagicMock()
            s = MagicMock()
            s.all.return_value = items
            r.scalars.return_value = s
            return r

        empty_select = MagicMock()
        empty_select.fetchall.return_value = []
        empty_legacy = MagicMock()
        empty_legacy.fetchone.return_value = None

        mock_db.execute.side_effect = [
            _make_scalars_result([template]),  # feishu templates
            empty_select,                      # resolved SELECT alert_card_messages (空)
            empty_legacy,                      # legacy fallback SELECT alert_history (空)
        ]

        alert_data = _make_alert_data(status="resolved")

        # prepare 返回 None → execute/save 都不执行
        await _run_three_stage(alert_data, mock_db)

        mock_feishu_svc.update_card_message.assert_not_called()
        mock_feishu_svc.send_p2p_card_message.assert_not_called()
        patched_save_message_id.assert_not_awaited()


class TestSendAlertOwnerLookupException:
    """★ 场景 3 (P0-A): DB 异常查负责人 → 仍标记 notification_sent=True ★

    历史根因: _get_asset_owner_open_id catch 异常 return None,
    若 else 分支不标记 → notification_sent 永远 False → 重复发送。
    修复: else 分支也调用 _update_alert_history_notification_sent。
    """

    async def test_owner_lookup_exception_marks_sent(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_owner_lookup,
        patched_group_lookup,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        """_get_asset_owner_open_id 内部异常被 catch 后 return None,
        通知组也返回空 → 进入 else 分支必须标记.

        注意: 真实 _get_asset_owner_open_id 内部 catch 异常并 return None,
        所以这里用 return_value=None 模拟异常后的行为,而非 side_effect。
        """

        alert_data = _make_alert_data(status="firing")

        # _run_three_stage 内部不应抛异常
        await _run_three_stage(alert_data, mock_db_with_feishu_template)

        # ★ 核心断言: 查询异常导致 return None/[] → else 分支必须标记 (P0-C 修复)
        patched_mark_sent.assert_awaited_once()
        mock_feishu_svc.send_p2p_card_message.assert_not_called()


class TestPreMarkBeforeSend:
    """★ 场景 5 (P0-B 顺序验证): 预占位标记严格在飞书发送前 ★

    历史根因: 旧代码标记在发送后,发送中异常导致未标记 → 重复发送。
    修复: _update_alert_history_notification_sent 移到 send_p2p_card_message 之前。
    """

    async def test_mark_sent_called_before_any_feishu_send(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ):
            call_sequence = []

            async def _mark_side_effect(db, alertname, instance, starts_at=None):
                call_sequence.append("mark_sent")
                return None

            def _send_side_effect(**kwargs):
                call_sequence.append("feishu_send")
                return {"success": True, "message_id": "om_x"}

            patched_mark_sent.side_effect = _mark_side_effect
            mock_feishu_svc.send_p2p_card_message.side_effect = _send_side_effect

            alert_data = _make_alert_data(status="firing")

            await _run_three_stage(alert_data, mock_db_with_feishu_template)

            # ★ 核心断言: mark_sent 必须在 feishu_send 之前
            assert "mark_sent" in call_sequence, "预占位标记必须被调用"
            assert "feishu_send" in call_sequence, "飞书发送必须被调用"
            assert call_sequence.index("mark_sent") < call_sequence.index("feishu_send"), (
                "预占位标记必须在飞书发送之前 (P0-B)"
            )


class TestAsyncioToThreadWrapper:
    """★ 场景 6 (P1-B): 飞书调用必须通过 asyncio.to_thread 包装 ★

    历史根因: 同步 send_p2p_card_message 在 async 函数中直接 await 阻塞事件循环,
    单次调用 25-30s,导致 Alertmanager webhook 超时重发。
    修复: asyncio.to_thread 包装 → 单请求从 330s 降至 74s。
    """

    async def test_feishu_send_wrapped_with_to_thread(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.alerts.notification_task.asyncio.to_thread",
            new=AsyncMock(),
        ) as mock_to_thread:
            mock_to_thread.return_value = {"success": True, "message_id": "om_thread_test"}

            alert_data = _make_alert_data(status="firing")

            await _run_three_stage(alert_data, mock_db_with_feishu_template)

            # ★ 核心断言: send_p2p_card_message 必须通过 asyncio.to_thread 调用
            mock_to_thread.assert_awaited()
            called_func = mock_to_thread.call_args.args[0]
            assert called_func == mock_feishu_svc.send_p2p_card_message, (
                "asyncio.to_thread 必须包装 send_p2p_card_message (P1-B)"
            )

    async def test_feishu_update_wrapped_with_to_thread(
        self,
        mock_db,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        """验证 resolved 时 update_card_message 通过 asyncio.to_thread 包装.

        三阶段架构:
        - prepare: 查询 alert_card_messages (1 次 SELECT, fetchall)
        - execute: update_card_message 通过 asyncio.to_thread
        - save: 被 patched_save_message_id 拦截，不执行真实 DB UPDATE
        """
        # 构造 2 次 execute 调用的返回值:
        # 1. feishu template query → [template]
        # 2. resolved SELECT alert_card_messages → rows(id, open_message_id, alert_history_id)
        template = _make_feishu_template(with_card_config=False)

        def _make_scalars_result(items):
            r = MagicMock()
            s = MagicMock()
            s.all.return_value = items
            r.scalars.return_value = s
            return r

        # row 格式: (acm.id, acm.open_message_id, acm.alert_history_id)
        select_result = MagicMock()
        row = MagicMock()
        row.__getitem__ = MagicMock(side_effect=lambda i: {0: 999, 1: "om_old", 2: 42}[i])
        select_result.fetchall.return_value = [row]

        mock_db.execute.side_effect = [
            _make_scalars_result([template]), # feishu templates
            select_result,                   # resolved SELECT alert_card_messages
        ]

        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.alerts.notification_task.asyncio.to_thread",
            new=AsyncMock(return_value={"success": True}),
        ) as mock_to_thread:
            alert_data = _make_alert_data(status="resolved")

            await _run_three_stage(alert_data, mock_db)

            mock_to_thread.assert_awaited()
            called_func = mock_to_thread.call_args.args[0]
            assert called_func == mock_feishu_svc.update_card_message, (
                "asyncio.to_thread 必须包装 update_card_message (P1-B)"
            )


class TestSendAlertSavesFirstMessageId:
    """场景 8: 多收件人时保存首个 message_id."""

    async def test_saves_first_successful_message_id(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=["ou_member1", "ou_member2"],
        ):
            # 三个收件人,返回不同 message_id
            mock_feishu_svc.send_p2p_card_message.side_effect = [
                {"success": True, "message_id": "om_first"},
                {"success": True, "message_id": "om_second"},
                {"success": False, "message_id": None},
            ]

            alert_data = _make_alert_data(status="firing")

            await _run_three_stage(alert_data, mock_db_with_feishu_template)

            # save_notification_result 被调用，result.sent_cards 包含所有成功发送的卡片
            patched_save_message_id.assert_awaited_once()
            # 三参数签名: (db, ctx, result)
            call_args = patched_save_message_id.call_args
            result_arg = call_args.args[2] if len(call_args.args) >= 3 else call_args.kwargs.get("result")
            # sent_cards 应包含 2 个成功发送的卡片（首个为 om_first）
            assert len(result_arg.sent_cards) == 2
            assert result_arg.sent_cards[0]["open_message_id"] == "om_first"
            assert result_arg.sent_cards[1]["open_message_id"] == "om_second"

    async def test_no_successful_send_does_not_save(
        self,
        mock_db_with_feishu_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
        mock_feishu_svc,
    ):
        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value="ou_owner",
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ):
            mock_feishu_svc.send_p2p_card_message.return_value = {"success": False, "message_id": None}

            alert_data = _make_alert_data(status="firing")

            await _run_three_stage(alert_data, mock_db_with_feishu_template)

            # 全部失败 → 不保存 message_id (但预占位标记仍执行)
            patched_mark_sent.assert_awaited_once()
            patched_save_message_id.assert_not_awaited()


# =============================================================================
# 补充: 内部辅助函数的直接单元测试 (覆盖函数内部所有分支)
# 之前 L3 测试通过 patch 这些函数模拟返回值,函数内部代码未被覆盖。
# 以下测试直接调用这些函数,通过 Mock DB session 覆盖内部逻辑。
# =============================================================================


class TestGetAssetOwnerOpenId:
    """覆盖 _get_asset_owner_open_id 内部分支."""

    async def test_empty_instance_returns_none(self):
        """instance 为空 → 直接返回 None (L556-557)."""
        db = AsyncMock()
        result = await _get_asset_owner_open_id(db, "")
        assert result is None
        db.execute.assert_not_called()

    async def test_non_ip_instance_returns_none(self):
        """instance 不是 IP 格式 → 返回 None (L559-561)."""
        db = AsyncMock()
        result = await _get_asset_owner_open_id(db, "not-an-ip")
        assert result is None
        db.execute.assert_not_called()

    async def test_valid_ip_with_owner_returns_open_id(self):
        """查询有结果且 user.feishu_open_id 存在 → 返回 open_id (L563-583)."""
        db = AsyncMock()
        asset = MagicMock()
        asset.name = "server-01"
        user = MagicMock()
        user.username = "admin"
        user.feishu_open_id = "ou_test_123"

        result_mock = MagicMock()
        result_mock.first.return_value = (asset, user)
        db.execute.return_value = result_mock

        result = await _get_asset_owner_open_id(db, "192.168.102.109")

        assert result == "ou_test_123"
        db.execute.assert_awaited_once()

    async def test_valid_ip_no_owner_returns_none(self):
        """查询无结果 → 返回 None (L585-589)."""
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.first.return_value = None
        db.execute.return_value = result_mock

        result = await _get_asset_owner_open_id(db, "192.168.102.200")

        assert result is None

    async def test_db_exception_returns_none(self):
        """DB 异常 → catch 后返回 None (L591-596)."""
        db = AsyncMock()
        db.execute.side_effect = ConnectionError("DB connection lost")

        result = await _get_asset_owner_open_id(db, "192.168.102.109")

        assert result is None

    async def test_owner_without_feishu_open_id_returns_none(self):
        """查询有结果但 user.feishu_open_id 为空 → 返回 None (L571-589)."""
        db = AsyncMock()
        asset = MagicMock()
        asset.name = "server-02"
        user = MagicMock()
        user.username = "user2"
        user.feishu_open_id = None

        result_mock = MagicMock()
        result_mock.first.return_value = (asset, user)
        db.execute.return_value = result_mock

        result = await _get_asset_owner_open_id(db, "192.168.102.110")

        assert result is None


class TestGetAlertNotificationGroupOpenIds:
    """覆盖 _get_alert_notification_group_open_ids 内部分支."""

    async def test_active_group_with_members_returns_open_ids(self):
        """活跃通知组有成员 → 返回 open_ids 列表 (L611-632)."""
        db = AsyncMock()

        member1 = MagicMock()
        member1.feishu_open_id = "ou_member1"
        member2 = MagicMock()
        member2.feishu_open_id = "ou_member2"

        group = MagicMock()
        group.is_active = True
        group.members = [member1, member2]

        with patch(
            "app.crud.crud_notification_group.notification_group.get_by_notification_type",
            new_callable=AsyncMock,
            return_value=[group],
        ):
            result = await _get_alert_notification_group_open_ids(db)

        assert result == ["ou_member1", "ou_member2"]

    async def test_inactive_group_skipped(self):
        """非活跃通知组被跳过 (L619 is_active 检查)."""
        db = AsyncMock()

        member = MagicMock()
        member.feishu_open_id = "ou_member1"

        group = MagicMock()
        group.is_active = False
        group.members = [member]

        with patch(
            "app.crud.crud_notification_group.notification_group.get_by_notification_type",
            new_callable=AsyncMock,
            return_value=[group],
        ):
            result = await _get_alert_notification_group_open_ids(db)

        assert result == []

    async def test_empty_groups_returns_empty_list(self):
        """无通知组 → 返回空列表."""
        db = AsyncMock()
        with patch(
            "app.crud.crud_notification_group.notification_group.get_by_notification_type",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await _get_alert_notification_group_open_ids(db)

        assert result == []

    async def test_member_dedup(self):
        """同一 open_id 在多组出现 → 去重 (L621 not in open_ids)."""
        db = AsyncMock()

        member1 = MagicMock()
        member1.feishu_open_id = "ou_shared"
        member2 = MagicMock()
        member2.feishu_open_id = "ou_shared"

        group1 = MagicMock()
        group1.is_active = True
        group1.members = [member1]
        group2 = MagicMock()
        group2.is_active = True
        group2.members = [member2]

        with patch(
            "app.crud.crud_notification_group.notification_group.get_by_notification_type",
            new_callable=AsyncMock,
            return_value=[group1, group2],
        ):
            result = await _get_alert_notification_group_open_ids(db)

        assert result == ["ou_shared"]

    async def test_db_exception_returns_empty_list(self):
        """DB 异常 → catch 后返回空列表 (L633-635)."""
        db = AsyncMock()
        with patch(
            "app.crud.crud_notification_group.notification_group.get_by_notification_type",
            new_callable=AsyncMock,
            side_effect=ConnectionError("DB connection lost"),
        ):
            result = await _get_alert_notification_group_open_ids(db)

        assert result == []


class TestUpdateAlertHistoryNotificationSent:
    """覆盖 _update_alert_history_notification_sent 内部分支."""

    async def test_existing_firing_record_updates_and_commits(self):
        """有 firing 记录 → UPDATE + commit (L510-529)."""
        db = AsyncMock()
        select_result = MagicMock()
        select_result.fetchone.return_value = (42,)
        db.execute.return_value = select_result

        await _update_alert_history_notification_sent(db, "HighCpu", "192.168.102.109")

        assert db.execute.await_count == 2
        db.commit.assert_awaited_once()

    async def test_no_firing_record_warns(self):
        """无 firing 记录 → warning,不执行 UPDATE (L530-534)."""
        db = AsyncMock()
        select_result = MagicMock()
        select_result.fetchone.return_value = None
        db.execute.return_value = select_result

        await _update_alert_history_notification_sent(db, "HighCpu", "192.168.102.109")

        assert db.execute.await_count == 1
        db.commit.assert_not_called()

    async def test_exception_triggers_rollback(self):
        """异常 → rollback (L536-543)."""
        db = AsyncMock()
        db.execute.side_effect = ConnectionError("DB connection lost")

        await _update_alert_history_notification_sent(db, "HighCpu", "192.168.102.109")

        db.rollback.assert_awaited_once()
