"""每日告警汇总任务单元测试：窗口计算 / 记录合并 / 卡片构建。"""

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.tasks.alert_summary_tasks import (
    yesterday_window,
    merge_alert_records,
    build_summary_markdown,
)

TZ = ZoneInfo("Asia/Shanghai")


def _rec(
    id: int,
    alertname: str,
    instance: str,
    severity: str,
    starts_at: datetime,
    status: str = "firing",
    ends_at: datetime | None = None,
    description: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        alertname=alertname,
        labels={"instance": instance},
        annotations={"description": description},
        severity=severity,
        starts_at=starts_at,
        ends_at=ends_at,
        status=status,
    )


def _dt(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=TZ)


class TestYesterdayWindow:
    def test_window_bounds(self):
        now = _dt(9, 18, 9, 5)
        start, end = yesterday_window(now)
        assert start == _dt(9, 17, 0, 0)
        assert end == _dt(9, 18, 0, 0)

    def test_window_on_midnight(self):
        start, end = yesterday_window(_dt(9, 18, 0, 0))
        assert start == _dt(9, 17, 0, 0)
        assert end == _dt(9, 18, 0, 0)


class TestMergeAlertRecords:
    def setup_method(self):
        self.w_start = _dt(9, 17, 0, 0)
        self.w_end = _dt(9, 18, 0, 0)

    def test_group_by_alertname_and_instance(self):
        records = [
            _rec(1, "HostDown", "10.0.0.1", "critical", _dt(9, 17, 8)),
            _rec(2, "HostDown", "10.0.0.2", "warning", _dt(9, 17, 9)),
            _rec(3, "HostDown", "10.0.0.1", "critical", _dt(9, 17, 12)),
        ]
        merged = merge_alert_records(records, self.w_start, self.w_end)
        assert len(merged) == 2
        g1 = next(g for g in merged if g["instance"] == "10.0.0.1")
        assert g1["fire_count"] == 2
        assert g1["has_firing"] is True

    def test_fire_count_only_counts_window(self):
        records = [
            # 窗口前的老告警（遗留），不计入昨日触发次数
            _rec(1, "HostDown", "10.0.0.1", "critical", _dt(9, 15, 8)),
            # 窗口内
            _rec(2, "HostDown", "10.0.0.1", "critical", _dt(9, 17, 8)),
        ]
        merged = merge_alert_records(records, self.w_start, self.w_end)
        assert merged[0]["fire_count"] == 1
        assert merged[0]["first_starts_at"] == _dt(9, 15, 8)

    def test_severity_takes_highest(self):
        records = [
            _rec(1, "CPUHigh", "10.0.0.1", "warning", _dt(9, 17, 8)),
            _rec(2, "CPUHigh", "10.0.0.1", "critical", _dt(9, 17, 10)),
        ]
        merged = merge_alert_records(records, self.w_start, self.w_end)
        assert merged[0]["severity"] == "critical"

    def test_description_takes_latest_record(self):
        records = [
            _rec(1, "CPUHigh", "10.0.0.1", "warning", _dt(9, 17, 8), description="旧描述"),
            _rec(2, "CPUHigh", "10.0.0.1", "warning", _dt(9, 17, 10), description="新描述"),
        ]
        merged = merge_alert_records(records, self.w_start, self.w_end)
        assert merged[0]["description"] == "新描述"

    def test_firing_wins_over_resolved(self):
        records = [
            _rec(1, "Flap", "10.0.0.1", "warning", _dt(9, 16, 8), status="resolved",
                 ends_at=_dt(9, 18, 1)),
            _rec(2, "Flap", "10.0.0.1", "warning", _dt(9, 17, 20), status="firing"),
        ]
        merged = merge_alert_records(records, self.w_start, self.w_end)
        assert merged[0]["has_firing"] is True
        assert merged[0]["resolved_at"] is None

    def test_resolved_after_window_end_marks_recovered(self):
        records = [
            _rec(1, "DiskFull", "10.0.0.9", "warning", _dt(9, 17, 10), status="resolved",
                 ends_at=_dt(9, 18, 7, 30)),
        ]
        merged = merge_alert_records(records, self.w_start, self.w_end)
        assert merged[0]["resolved_at"] == _dt(9, 18, 7, 30)
        assert merged[0]["has_firing"] is False


class TestBuildSummaryMarkdown:
    def setup_method(self):
        self.w_start = _dt(9, 17, 0, 0)
        self.w_end = _dt(9, 18, 0, 0)

    def test_empty_summary(self):
        md = build_summary_markdown([], self.w_start, self.w_end)
        assert "无未解决告警" in md
        assert "09-17" in md

    def test_critical_before_warning(self):
        merged = [
            {"alertname": "CPUHigh", "instance": "10.0.0.1", "severity": "warning",
             "fire_count": 1, "first_starts_at": _dt(9, 17, 8), "description": "",
             "resolved_at": None},
            {"alertname": "HostDown", "instance": "10.0.0.2", "severity": "critical",
             "fire_count": 2, "first_starts_at": _dt(9, 17, 9), "description": "宕机",
             "resolved_at": None},
        ]
        md = build_summary_markdown(merged, self.w_start, self.w_end)
        assert md.index("HostDown") < md.index("CPUHigh")
        assert "严重（critical）— 1 条" in md
        assert "警告（warning）— 1 条" in md

    def test_resolved_state_annotation(self):
        merged = [
            {"alertname": "DiskFull", "instance": "10.0.0.9", "severity": "warning",
             "fire_count": 1, "first_starts_at": _dt(9, 17, 10), "description": "",
             "resolved_at": _dt(9, 18, 7, 30)},
        ]
        md = build_summary_markdown(merged, self.w_start, self.w_end)
        assert "今日 07:30 已恢复" in md

    def test_zero_fire_count_omits_count(self):
        merged = [
            {"alertname": "OldAlert", "instance": "10.0.0.1", "severity": "warning",
             "fire_count": 0, "first_starts_at": _dt(9, 15, 8), "description": "",
             "resolved_at": None},
        ]
        md = build_summary_markdown(merged, self.w_start, self.w_end)
        assert "昨日触发" not in md

    def test_truncates_beyond_max_items(self):
        from app.tasks.alert_summary_tasks import CARD_MAX_ITEMS

        merged = [
            {"alertname": f"A{i}", "instance": "10.0.0.1", "severity": "warning",
             "fire_count": 1, "first_starts_at": _dt(9, 17, 8), "description": "",
             "resolved_at": None}
            for i in range(CARD_MAX_ITEMS + 5)
        ]
        md = build_summary_markdown(merged, self.w_start, self.w_end)
        assert f"其余 {len(merged) - CARD_MAX_ITEMS} 条已省略" in md


class TestDailyAlertSummaryTask:
    """任务级行为: 无未解决告警时跳过通知。"""

    async def test_zero_alerts_skips_notification(self):
        from unittest.mock import AsyncMock, patch

        from app.tasks.alert_summary_tasks import daily_alert_summary_task

        summary = {"total": 0, "card": {}, "chat_id": "", "recipient_open_ids": []}
        with (
            patch(
                "app.tasks.alert_summary_tasks.db_operation_with_retry",
                new=AsyncMock(return_value=summary),
            ),
            patch(
                "app.tasks.alert_summary_tasks._send_summary", new=AsyncMock()
            ) as send_mock,
        ):
            result = await daily_alert_summary_task()

        assert result["status"] == "success"
        assert result["total"] == 0
        assert "未发送通知" in result["result_summary"]
        send_mock.assert_not_awaited()

    async def test_nonzero_alerts_sends_notification(self):
        from unittest.mock import AsyncMock, patch

        from app.tasks.alert_summary_tasks import daily_alert_summary_task

        summary = {"total": 3, "card": {}, "chat_id": "", "recipient_open_ids": []}
        with (
            patch(
                "app.tasks.alert_summary_tasks.db_operation_with_retry",
                new=AsyncMock(return_value=summary),
            ),
            patch(
                "app.tasks.alert_summary_tasks._send_summary",
                new=AsyncMock(return_value={"chat_ok": True, "p2p_sent": 2, "p2p_failed": 0}),
            ) as send_mock,
        ):
            result = await daily_alert_summary_task()

        assert result["status"] == "success"
        assert result["total"] == 3
        send_mock.assert_awaited_once()
