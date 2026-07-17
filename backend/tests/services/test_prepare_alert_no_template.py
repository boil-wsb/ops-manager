"""L2 单元测试: prepare_alert_notification 无模板分支.

★ NC-3 修复测试 (第二轮审查) ★

第一性原理覆盖的不变式:
- 一致性: 无 feishu_template 时也必须调用 _update_alert_history_notification_sent
  并传 starts_at=starts_at（NC-3 修复点）。
- 可达性: 无模板场景不应导致跨周期/跨告警的误标记。

NC-3 根因:
- C-02 给 _update_alert_history_notification_sent 加了 starts_at 参数
- 但 prepare_alert_notification 的"无 feishu_template"分支调用时未传 starts_at
- 走 _update_alert_history_notification_sent 内部 else 退化路径（无 starts_at 过滤、
  无 status 过滤），可能误标记其他周期/其他告警的 firing 记录为 notification_sent=True
- 造成告警永久丢失

修复: 无模板分支也传 starts_at=starts_at（datetime 对象）。
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alerts.notification_task import prepare_alert_notification


@pytest.fixture
def patched_mark_sent():
    with patch(
        "app.services.alerts.notification_task._update_alert_history_notification_sent",
        new_callable=AsyncMock,
    ) as fn:
        yield fn


class TestNoTemplateBranchMarksSent:
    """NC-3: 无模板分支也必须传 starts_at 调用 _update_alert_history_notification_sent."""

    async def test_no_template_branch_passes_starts_at(self, patched_mark_sent):
        """无 feishu_template 时,_update_alert_history_notification_sent 必须收到 starts_at."""
        # mock_db: feishu_templates 返回空列表
        db = AsyncMock()
        empty_result = MagicMock()
        empty_scalars = MagicMock()
        empty_scalars.all.return_value = []
        empty_result.scalars.return_value = empty_scalars
        db.execute.return_value = empty_result

        starts_at_iso = "2026-07-16T10:00:00+00:00"
        alert_data = {
            "alertname": "HighCpu",
            "instance": "192.168.1.10",
            "status": "firing",
            "severity": "critical",
            "description": "CPU > 90%",
            "starts_at": starts_at_iso,
            "labels": {
                "alertname": "HighCpu",
                "severity": "critical",
                "instance": "192.168.1.10",
            },
            "annotations": {"description": "CPU > 90%"},
            "is_suppressed": False,
            "silence_id": None,
            "history_id": 1,
        }

        result = await prepare_alert_notification(db, alert_data)

        # 无模板 → 返回 None
        assert result is None
        # ★ NC-3 核心断言: 必须调用 _update_alert_history_notification_sent 且 starts_at 非 None
        patched_mark_sent.assert_awaited_once()
        call_kwargs = patched_mark_sent.await_args.kwargs
        assert "starts_at" in call_kwargs, "NC-3: 必须传 starts_at 参数"
        assert call_kwargs["starts_at"] is not None, "NC-3: starts_at 不能为 None"
        # starts_at 应为 datetime 对象（由 prepare_alert_notification 内部 fromisoformat 解析）
        assert isinstance(call_kwargs["starts_at"], datetime), (
            "NC-3: starts_at 应为 datetime 对象，而非字符串"
        )
        # 验证 starts_at 值正确
        expected_dt = datetime.fromisoformat(starts_at_iso.replace("Z", "+00:00"))
        assert call_kwargs["starts_at"] == expected_dt

    async def test_no_template_branch_skips_mark_sent_for_resolved(self, patched_mark_sent):
        """NC-3 边界: 无模板 + status=resolved → 不调用 _update_alert_history_notification_sent.

        修复代码: if status != "resolved": await _update_alert_history_notification_sent(...)
        resolved 不需要预占位标记（resolved 通知是更新已有卡片，不存在重复触发风险）。
        """
        db = AsyncMock()
        empty_result = MagicMock()
        empty_scalars = MagicMock()
        empty_scalars.all.return_value = []
        empty_result.scalars.return_value = empty_scalars
        db.execute.return_value = empty_result

        alert_data = {
            "alertname": "HighCpu",
            "instance": "192.168.1.10",
            "status": "resolved",
            "severity": "critical",
            "description": "CPU > 90%",
            "starts_at": "2026-07-16T10:00:00+00:00",
            "labels": {
                "alertname": "HighCpu",
                "severity": "critical",
                "instance": "192.168.1.10",
            },
            "annotations": {},
            "is_suppressed": False,
            "silence_id": None,
            "history_id": 1,
        }

        result = await prepare_alert_notification(db, alert_data)

        assert result is None
        # resolved 不调用 mark_sent
        patched_mark_sent.assert_not_awaited()
