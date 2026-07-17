"""
L6 失败路径测试: 异常场景下的一致性保障.

★ 这是 192.168.102.109 重复发送 bug 的防御性测试 ★
★ 迁移自 send_alert_notification 单体函数 → 三阶段分离架构 ★

第一性原理覆盖的不变式:
- 一致性: 即使发送失败,notification_sent 也必须被标记 (避免重复触发)
- 可达性: 失败不应导致告警被静默丢弃
- 隔离性 (P0-A): 单个 alert 失败不应污染后续 alert 的 DB session

历史根因:
- _get_asset_owner_open_id 异常 catch + return None → 进入 else 分支
- 旧 else 分支未标记 notification_sent → 永远 False → 17 张重复卡片
- 修复: else 分支也调用 _update_alert_history_notification_sent

覆盖路径:
1. _get_asset_owner_open_id 异常 → else 分支标记 notification_sent=True
2. _get_alert_notification_group_open_ids 异常 → else 分支标记
3. 飞书 send_p2p_card_message 返回 success=False → 预占位标记已生效
4. 飞书 send_p2p_card_message 抛异常 → execute 内部 catch,预占位标记已生效
5. _update_alert_history_notification_sent 异常 → 调用 db.rollback()
6. 飞书 update_card_message 失败 → save_notification_result 不被调用
7. 多个 alert 在同一 webhook 中,首个失败不影响后续
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alerts.notification_task import (
    _save_firing_alert_card_messages,
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
) -> dict:
    return {
        "alertname": "HighCpu",
        "status": status,
        "severity": "critical",
        "instance": instance,
        "description": "CPU usage > 90%",
        "starts_at": "2026-07-16T10:00:00+00:00",
        "labels": {"alertname": "HighCpu", "severity": "critical", "instance": instance},
        "annotations": {"description": "CPU usage > 90%"},
        "is_suppressed": False,
        "silence_id": None,
        "history_id": 1,
    }


def _make_feishu_template():
    """构造 AlertTemplate mock."""
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


@pytest.fixture
def mock_db():
    """基础 Mock AsyncSession,无预设返回值."""
    return AsyncMock()


@pytest.fixture
def mock_db_with_template():
    """Mock DB 返回 feishu 模板.

    新架构 prepare_alert_notification 只查询 feishu 模板（1 次 execute）。
    """
    db = AsyncMock()
    template = _make_feishu_template()
    feishu_result = MagicMock()
    feishu_scalars = MagicMock()
    feishu_scalars.all.return_value = [template]
    feishu_result.scalars.return_value = feishu_scalars

    db.execute.side_effect = [feishu_result]
    return db


@pytest.fixture
def patched_template_render():
    with patch(
        "app.services.alerts.notification_task.alert_template_service"
    ) as svc:
        svc.render_alert_template = AsyncMock(return_value=("告警", "正文"))
        svc.render_template = MagicMock(return_value='{"schema":"2.0"}')
        yield svc


@pytest.fixture
def patched_mark_sent():
    with patch(
        "app.services.alerts.notification_task._update_alert_history_notification_sent",
        new_callable=AsyncMock,
    ) as fn:
        yield fn


@pytest.fixture
def patched_save_message_id():
    """patch save_notification_result (阶段 3).

    注意: _run_three_stage 在测试模块内调用 save_notification_result，
    所以必须 patch 测试模块的引用，而非源模块的引用（Python mock 陷阱）。
    """
    with patch(
        "tests.services.test_alert_failure_paths.save_notification_result",
        new_callable=AsyncMock,
    ) as fn:
        yield fn


class TestOwnerLookupException:
    """★ 场景 1 (P0-C 根因): _get_asset_owner_open_id 异常 → else 分支标记 ★

    根因复现: DB 连接异常 → _get_asset_owner_open_id catch return None
    旧代码 else 分支仅日志,未标记 → 17 张重复卡片
    修复: else 分支调用 _update_alert_history_notification_sent
    """

    async def test_owner_lookup_exception_triggers_mark_sent(
        self,
        mock_db_with_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
    ):
        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            # _get_asset_owner_open_id 内部 catch 异常后 return None
            # 用 return_value=None 模拟异常后的真实行为
            feishu_svc = MagicMock()
            feishu_svc.send_p2p_card_message = MagicMock()
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            alert_data = _make_alert_data(status="firing")

            # 不应抛异常
            await _run_three_stage(alert_data, mock_db_with_template)

            # ★ 核心断言: else 分支必须标记 notification_sent=True (P0-C 修复)
            patched_mark_sent.assert_awaited_once()
            # 不应调用飞书发送
            feishu_svc.send_p2p_card_message.assert_not_called()


class TestGroupLookupException:
    """★ 场景 2 (P0-C 根因变体): 通知组查询异常 → else 分支标记 ★"""

    async def test_group_lookup_exception_triggers_mark_sent(
        self,
        mock_db_with_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
    ):
        with patch(
            "app.services.alerts.notification_task._get_asset_owner_open_id",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.alerts.notification_task._get_alert_notification_group_open_ids",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            # _get_alert_notification_group_open_ids 内部 catch 异常后 return []
            # 用 return_value=[] 模拟异常后的真实行为
            feishu_svc = MagicMock()
            feishu_svc.send_p2p_card_message = MagicMock()
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            alert_data = _make_alert_data(status="firing")

            await _run_three_stage(alert_data, mock_db_with_template)

            # ★ 核心断言: 查询异常 → return [] → 无收件人 → else 标记
            patched_mark_sent.assert_awaited_once()
            feishu_svc.send_p2p_card_message.assert_not_called()


class TestFeishuSendFailure:
    """场景 3: 飞书 send_p2p_card_message 返回 success=False → 预占位标记已生效."""

    async def test_feishu_send_failure_keeps_pre_mark(
        self,
        mock_db_with_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
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
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            feishu_svc = MagicMock()
            # 飞书发送失败
            feishu_svc.send_p2p_card_message = MagicMock(
                return_value={"success": False, "message_id": None}
            )
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            alert_data = _make_alert_data(status="firing")

            await _run_three_stage(alert_data, mock_db_with_template)

            # ★ 核心断言: 预占位标记在发送前已执行,飞书失败不影响标记
            patched_mark_sent.assert_awaited_once()
            # 全部失败 → needs_save=False → 不调用 save_notification_result
            patched_save_message_id.assert_not_awaited()


class TestFeishuSendException:
    """场景 4: 飞书 send_p2p_card_message 抛异常 → execute 内部 catch,预占位标记已生效.

    三阶段架构下 execute_feishu_notification 对每个收件人的异常单独 catch,
    异常不会传播到 _run_three_stage。result.needs_save=False (sent_cards 为空)。
    """

    async def test_feishu_send_exception_keeps_pre_mark(
        self,
        mock_db_with_template,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
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
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory:
            feishu_svc = MagicMock()
            # 飞书发送抛异常
            feishu_svc.send_p2p_card_message = MagicMock(
                side_effect=RuntimeError("lark API timeout")
            )
            feishu_svc.build_alert_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            alert_data = _make_alert_data(status="firing")

            # execute_feishu_notification 内部对每个收件人的异常单独 catch,
            # 异常不会传播。但 sent_cards 为空 → needs_save=False → 不调用 save。
            await _run_three_stage(alert_data, mock_db_with_template)

            # ★ 核心断言: 即使飞书发送抛异常,预占位标记已生效 (P0-B)
            patched_mark_sent.assert_awaited_once()
            # sent_cards 为空 → needs_save=False → 不调用 save_notification_result
            patched_save_message_id.assert_not_awaited()


class TestUpdateNotificationSentException:
    """★ 场景 5: _update_alert_history_notification_sent 异常 → 调用 db.rollback() ★

    修复: except 中添加 db.rollback() 避免 PendingRollbackError 扩散
    """

    async def test_update_notification_sent_exception_calls_rollback(self):
        """直接测试 _update_alert_history_notification_sent 的异常处理."""

        mock_db = AsyncMock()
        # db.execute 抛异常
        mock_db.execute.side_effect = RuntimeError("Postgres connection lost")

        # 不应抛异常(内部 catch)
        await _update_alert_history_notification_sent(
            db=mock_db,
            alertname="HighCpu",
            instance="192.168.102.109",
        )

        # ★ 核心断言: 异常时调用 db.rollback()
        mock_db.rollback.assert_awaited()

    async def test_update_notification_sent_no_firing_record_logs_warning(self):
        """无 firing 记录时只记日志,不抛异常."""
        mock_db = AsyncMock()
        result = MagicMock()
        row_mock = MagicMock()
        row_mock.__getitem__ = MagicMock(return_value=None)
        result.fetchone.return_value = None
        mock_db.execute.return_value = result

        # 不应抛异常
        await _update_alert_history_notification_sent(
            db=mock_db,
            alertname="NotExist",
            instance="10.0.0.1",
        )

        # 无记录 → 不调用 UPDATE
        assert mock_db.execute.await_count == 1  # 只 SELECT,不 UPDATE


class TestResolvedCardUpdateFailure:
    """场景 6: 飞书 update_card_message 失败 → save_notification_result 不被调用.

    三阶段架构下:
    - execute: update_card_message 返回 success=False → updated_card_message_ids 为空
    - result.needs_save = False → _run_three_stage 不调用 save_notification_result
    - 因此 DB 不会被更新（card_status 保持 'firing'）
    """

    async def test_resolved_card_update_failure_does_not_save(
        self,
        mock_db,
        patched_template_render,
        patched_mark_sent,
        patched_save_message_id,
    ):
        """resolved 时 update_card_message 失败 → save_notification_result 不被调用."""
        # 构造 DB execute 返回值:
        # 1. feishu template query → [template]
        # 2. resolved SELECT alert_card_messages → rows
        template = _make_feishu_template()

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
            _make_scalars_result([template]),  # feishu templates
            select_result,                     # resolved SELECT alert_card_messages
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
            "app.services.alerts.notification_task.get_feishu_notification_service"
        ) as feishu_factory, patch(
            "app.services.alerts.notification_task.asyncio.to_thread",
            new=AsyncMock(return_value={"success": False, "error": "card not found"}),
        ):
            feishu_svc = MagicMock()
            feishu_svc.build_resolved_card = MagicMock(return_value={"schema": "2.0"})
            feishu_factory.return_value = feishu_svc

            alert_data = _make_alert_data(status="resolved")

            # 不应抛异常
            await _run_three_stage(alert_data, mock_db)

            # ★ 核心断言: update_card_message 失败 → needs_save=False → 不调用 save
            patched_save_message_id.assert_not_awaited()


class TestSaveFiringCardMessagesException:
    """场景 7: _save_firing_alert_card_messages 异常 → 不影响主流程.

    旧名 _save_firing_alert_message_id 已重命名为 _save_firing_alert_card_messages,
    签名变更: (db, alertname, instance, sent_cards, history_id) 替代旧的
    (db, alertname, instance, severity, message_id)。
    """

    async def test_save_card_messages_exception_does_not_propagate(self):
        """_save_firing_alert_card_messages 异常被内部 catch,不传播."""

        mock_db = AsyncMock()
        # INSERT 抛异常 (history_id 已传入,跳过 SELECT,直接 INSERT)
        mock_db.execute.side_effect = [RuntimeError("connection lost")]

        # 不应抛异常(内部 catch)
        await _save_firing_alert_card_messages(
            db=mock_db,
            alertname="HighCpu",
            instance="192.168.102.109",
            sent_cards=[{"open_message_id": "om_test", "recipient_open_id": "ou_owner"}],
            history_id=1,
        )

        # 尝试了 INSERT(失败)
        assert mock_db.execute.await_count == 1
        # INSERT 失败 → 不调用 commit
        mock_db.commit.assert_not_awaited()
        # INSERT 失败 → 调用 rollback
        mock_db.rollback.assert_awaited()


class TestIndependentSessionIsolation:
    """★ 场景 8 (P0-A): 独立 DB session - 单个 alert 失败不污染后续 ★

    根因: alerts.py 在 for 循环中复用同一 session,
    首个 alert 失败导致 session 进 rollback 状态,
    后续 alert 全部受 PendingRollbackError 影响。
    修复: 每个 alert 使用 db_operation_with_retry 创建独立 session。
    """

    async def test_db_operation_with_retry_creates_independent_sessions(self):
        """验证 db_operation_with_retry 每次创建独立 session."""
        from app.db.session import db_operation_with_retry

        sessions = []

        async def _op(session):
            sessions.append(session)
            return len(sessions)

        # 两次调用应创建两个不同的 session
        result1 = await db_operation_with_retry(_op, max_retries=0, retry_delay=0.1)
        result2 = await db_operation_with_retry(_op, max_retries=0, retry_delay=0.1)

        assert result1 == 1
        assert result2 == 2
        # 两个 session 是不同的对象
        assert sessions[0] is not sessions[1], (
            "每个 alert 应使用独立 DB session (P0-A)"
        )

    async def test_db_operation_with_retry_does_not_propagate_transient_error(self):
        """验证瞬态错误触发重试,不污染后续调用."""
        from app.db.session import db_operation_with_retry

        call_count = 0

        async def _op(session):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次抛瞬态错误
                raise ConnectionError("simulated connection lost")
            return "success"

        result = await db_operation_with_retry(_op, max_retries=2, retry_delay=0.1)

        assert result == "success"
        assert call_count == 2, "瞬态错误应触发重试"

    async def test_db_operation_with_retry_non_transient_error_raised(self):
        """验证非瞬态错误立即抛出,不重试."""
        from sqlalchemy.exc import IntegrityError

        from app.db.session import db_operation_with_retry

        async def _op(session):
            raise IntegrityError("statement", {}, Exception("duplicate key"))

        with pytest.raises(IntegrityError):
            await db_operation_with_retry(_op, max_retries=2, retry_delay=0.1)
