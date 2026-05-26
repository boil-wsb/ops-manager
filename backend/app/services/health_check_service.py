"""
Health check service - collect metrics, evaluate status, save reports, send notifications.
"""

import json
from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.db.session import db_operation_with_retry
from app.integrations.feishu.service import get_feishu_service
from app.services.prometheus.client import get_prometheus_client

logger = get_logger(__name__)

DEFAULT_THRESHOLDS = {
    "cpu_load_per_core_warning": 0.8,
    "cpu_load_per_core_critical": 1.5,
    "memory_usage_warning": 80,
    "memory_usage_critical": 95,
    "disk_usage_warning": 80,
    "disk_usage_critical": 95,
}


class HealthCheckService:
    async def generate_health_report(self) -> "HealthCheckReport":
        """Execute full health check: collect -> evaluate -> save -> notify"""

        # 1. Read thresholds from system_configs
        thresholds_value = await db_operation_with_retry(
            self._read_thresholds_config, max_retries=2, retry_delay=1.0
        )

        thresholds = DEFAULT_THRESHOLDS.copy()
        if thresholds_value:
            try:
                custom = json.loads(thresholds_value)
                thresholds.update(custom)
            except (json.JSONDecodeError, TypeError):
                logger.warning("解析阈值配置失败，使用默认值", extra={"action": "health_check.run"})

        # 2. Collect server metrics
        client = get_prometheus_client()
        server_metrics = []
        try:
            server_metrics = await client.get_all_nodes_health_check()
            logger.info(f"采集服务器指标: {len(server_metrics)} 台", extra={"action": "health_check.run", "server_count": len(server_metrics)})
        except Exception as e:
            logger.error(f"采集服务器指标失败: {e}", extra={"action": "health_check.run"})

        # 3. Collect terminal metrics
        terminal_metrics = []
        try:
            terminal_metrics = await client.get_all_terminals_with_metrics()
            logger.info(f"采集终端指标: {len(terminal_metrics)} 台", extra={"action": "health_check.run", "terminal_count": len(terminal_metrics)})
        except Exception as e:
            logger.error(f"采集终端指标失败: {e}", extra={"action": "health_check.run"})

        # 4. Evaluate each host status
        host_results = []
        for metrics in server_metrics:
            result = self._evaluate_host_status(metrics, thresholds, asset_type="server")
            host_results.append(result)

        for metrics in terminal_metrics:
            result = self._evaluate_host_status(
                metrics, thresholds, asset_type="terminal"
            )
            host_results.append(result)

        # 5. Build summary
        ok_count = sum(1 for r in host_results if r["host_status"] == "ok")
        warning_count = sum(1 for r in host_results if r["host_status"] == "warning")
        critical_count = sum(1 for r in host_results if r["host_status"] == "critical")
        total_hosts = len(host_results)

        summary = {
            "total_hosts": total_hosts,
            "ok_count": ok_count,
            "warning_count": warning_count,
            "critical_count": critical_count,
        }

        # 6. Save report to database
        report = await self._save_report(summary, host_results)

        # 7. Send feishu notification
        try:
            await self._send_feishu_notification(report)
        except Exception as e:
            logger.error(f"发送飞书通知失败: {e}", extra={"action": "health_check.notify"})

        # 8. Return the report
        return report

    async def _read_thresholds_config(self, db):
        from app.crud.crud_system_config import crud_system_config

        await self._ensure_default_thresholds(db)
        return await crud_system_config.get_value(db, "health_check.thresholds")

    def _evaluate_host_status(
        self, metrics: dict, thresholds: dict, asset_type: str = "server"
    ) -> dict:
        """Evaluate a single host's status based on thresholds.

        Returns dict with: host_status, check_details, and original metrics.
        """
        check_details = []
        host_status = "ok"

        if asset_type == "server":
            instance = metrics.get("instance", "")
            nodename = metrics.get("nodename", "")
            is_online = metrics.get("is_online", False)
            cpu_count = metrics.get("cpu_cores", 1) or 1
            load1 = metrics.get("load1", 0.0) or 0.0
            memory_usage_percent = metrics.get("memory_usage_percent", 0.0) or 0.0
            disk_usage_percent = metrics.get("disk_usage_percent", 0.0) or 0.0

            # Check is_online
            if not is_online:
                check_details.append(
                    {
                        "name": "在线状态",
                        "status": "critical",
                        "value": "离线",
                        "threshold": "在线",
                    }
                )
                host_status = "critical"
            else:
                check_details.append(
                    {
                        "name": "在线状态",
                        "status": "ok",
                        "value": "在线",
                        "threshold": "在线",
                    }
                )

            # Check CPU load per core
            load_per_core = load1 / cpu_count if cpu_count > 0 else 0
            cpu_critical = thresholds.get("cpu_load_per_core_critical", 1.5)
            cpu_warning = thresholds.get("cpu_load_per_core_warning", 0.8)
            if load_per_core > cpu_critical:
                check_details.append(
                    {
                        "name": "CPU负载",
                        "status": "critical",
                        "value": f"{load_per_core:.2f}",
                        "threshold": f">{cpu_critical}",
                    }
                )
                host_status = "critical"
            elif load_per_core > cpu_warning:
                check_details.append(
                    {
                        "name": "CPU负载",
                        "status": "warning",
                        "value": f"{load_per_core:.2f}",
                        "threshold": f">{cpu_warning}",
                    }
                )
                if host_status != "critical":
                    host_status = "warning"
            else:
                check_details.append(
                    {
                        "name": "CPU负载",
                        "status": "ok",
                        "value": f"{load_per_core:.2f}",
                        "threshold": f">{cpu_warning}",
                    }
                )

            # Check memory usage
            mem_critical = thresholds.get("memory_usage_critical", 95)
            mem_warning = thresholds.get("memory_usage_warning", 80)
            if memory_usage_percent > mem_critical:
                check_details.append(
                    {
                        "name": "内存使用率",
                        "status": "critical",
                        "value": f"{memory_usage_percent:.1f}%",
                        "threshold": f">{mem_critical}%",
                    }
                )
                host_status = "critical"
            elif memory_usage_percent > mem_warning:
                check_details.append(
                    {
                        "name": "内存使用率",
                        "status": "warning",
                        "value": f"{memory_usage_percent:.1f}%",
                        "threshold": f">{mem_warning}%",
                    }
                )
                if host_status != "critical":
                    host_status = "warning"
            else:
                check_details.append(
                    {
                        "name": "内存使用率",
                        "status": "ok",
                        "value": f"{memory_usage_percent:.1f}%",
                        "threshold": f">{mem_warning}%",
                    }
                )

            # Check disk usage
            disk_critical = thresholds.get("disk_usage_critical", 95)
            disk_warning = thresholds.get("disk_usage_warning", 80)
            if disk_usage_percent > disk_critical:
                check_details.append(
                    {
                        "name": "磁盘使用率",
                        "status": "critical",
                        "value": f"{disk_usage_percent:.1f}%",
                        "threshold": f">{disk_critical}%",
                    }
                )
                host_status = "critical"
            elif disk_usage_percent > disk_warning:
                check_details.append(
                    {
                        "name": "磁盘使用率",
                        "status": "warning",
                        "value": f"{disk_usage_percent:.1f}%",
                        "threshold": f">{disk_warning}%",
                    }
                )
                if host_status != "critical":
                    host_status = "warning"
            else:
                check_details.append(
                    {
                        "name": "磁盘使用率",
                        "status": "ok",
                        "value": f"{disk_usage_percent:.1f}%",
                        "threshold": f">{disk_warning}%",
                    }
                )

            return {
                "instance": instance,
                "nodename": nodename,
                "asset_type": asset_type,
                "host_status": host_status,
                "check_details": check_details,
                "os_info": f"{metrics.get('sysname', '')} {metrics.get('machine', '')}".strip(),
                "kernel_version": metrics.get("release", ""),
                "cpu_count": cpu_count,
                "cpu_usage": metrics.get("cpu_usage_percent", 0.0),
                "load1": metrics.get("load1", 0.0),
                "load5": metrics.get("load5", 0.0),
                "load15": metrics.get("load15", 0.0),
                "memory_usage": memory_usage_percent,
                "memory_total_mb": metrics.get("memory_total_mb", 0.0),
                "memory_used_mb": round(
                    (metrics.get("memory_total_mb", 0.0) or 0.0)
                    * (memory_usage_percent / 100),
                    2,
                ),
                "disk_usage": disk_usage_percent,
                "disk_total_gb": metrics.get("disk_total_gb", 0.0),
                "is_online": is_online,
            }

        else:  # terminal
            hostname = metrics.get("hostname", "")
            instance = metrics.get("ip_address", "") or metrics.get("hostname", "")
            cpu_usage = metrics.get("cpu_usage", 0.0) or 0.0
            memory_usage = metrics.get("memory_usage", 0.0) or 0.0
            disk_usage = metrics.get("disk_usage", 0.0) or 0.0

            mem_critical = thresholds.get("memory_usage_critical", 95)
            mem_warning = thresholds.get("memory_usage_warning", 80)
            disk_critical = thresholds.get("disk_usage_critical", 95)
            disk_warning = thresholds.get("disk_usage_warning", 80)

            # Check CPU usage
            cpu_critical = thresholds.get("memory_usage_critical", 95)
            cpu_warning = thresholds.get("memory_usage_warning", 80)
            # For terminals, use the same warning/critical thresholds for CPU
            if cpu_usage > cpu_critical:
                check_details.append(
                    {
                        "name": "CPU使用率",
                        "status": "critical",
                        "value": f"{cpu_usage:.1f}%",
                        "threshold": f">{cpu_critical}%",
                    }
                )
                host_status = "critical"
            elif cpu_usage > cpu_warning:
                check_details.append(
                    {
                        "name": "CPU使用率",
                        "status": "warning",
                        "value": f"{cpu_usage:.1f}%",
                        "threshold": f">{cpu_warning}%",
                    }
                )
                if host_status != "critical":
                    host_status = "warning"
            else:
                check_details.append(
                    {
                        "name": "CPU使用率",
                        "status": "ok",
                        "value": f"{cpu_usage:.1f}%",
                        "threshold": f">{cpu_warning}%",
                    }
                )

            # Check memory usage
            if memory_usage > mem_critical:
                check_details.append(
                    {
                        "name": "内存使用率",
                        "status": "critical",
                        "value": f"{memory_usage:.1f}%",
                        "threshold": f">{mem_critical}%",
                    }
                )
                host_status = "critical"
            elif memory_usage > mem_warning:
                check_details.append(
                    {
                        "name": "内存使用率",
                        "status": "warning",
                        "value": f"{memory_usage:.1f}%",
                        "threshold": f">{mem_warning}%",
                    }
                )
                if host_status != "critical":
                    host_status = "warning"
            else:
                check_details.append(
                    {
                        "name": "内存使用率",
                        "status": "ok",
                        "value": f"{memory_usage:.1f}%",
                        "threshold": f">{mem_warning}%",
                    }
                )

            # Check disk usage
            if disk_usage > disk_critical:
                check_details.append(
                    {
                        "name": "磁盘使用率",
                        "status": "critical",
                        "value": f"{disk_usage:.1f}%",
                        "threshold": f">{disk_critical}%",
                    }
                )
                host_status = "critical"
            elif disk_usage > disk_warning:
                check_details.append(
                    {
                        "name": "磁盘使用率",
                        "status": "warning",
                        "value": f"{disk_usage:.1f}%",
                        "threshold": f">{disk_warning}%",
                    }
                )
                if host_status != "critical":
                    host_status = "warning"
            else:
                check_details.append(
                    {
                        "name": "磁盘使用率",
                        "status": "ok",
                        "value": f"{disk_usage:.1f}%",
                        "threshold": f">{disk_warning}%",
                    }
                )

            return {
                "instance": instance,
                "nodename": hostname,
                "asset_type": asset_type,
                "host_status": host_status,
                "check_details": check_details,
                "os_info": metrics.get("os_caption", ""),
                "kernel_version": metrics.get("os_version", ""),
                "cpu_count": None,
                "cpu_usage": cpu_usage,
                "load1": None,
                "load5": None,
                "load15": None,
                "memory_usage": memory_usage,
                "memory_total_mb": round(
                    (metrics.get("memory_total", 0.0) or 0.0) / 1024 / 1024, 2
                ),
                "memory_used_mb": None,
                "disk_usage": disk_usage,
                "disk_total_gb": round(
                    (metrics.get("disk_total", 0.0) or 0.0) / 1024 / 1024 / 1024, 2
                ),
                "is_online": True,
            }

    async def _save_report(
        self, summary: dict, host_results: list[dict]
    ) -> "HealthCheckReport":
        """Save report and details to database"""

        return await db_operation_with_retry(
            lambda db: self._save_report_db(db, summary, host_results),
            max_retries=3, retry_delay=2.0,
        )

    async def _save_report_db(self, db, summary, host_results):
        from app.models.health_check import HealthCheckDetail, HealthCheckReport

        now = datetime.now(ZoneInfo("Asia/Shanghai"))

        report = HealthCheckReport(
            report_time=now,
            source="prometheus",
            total_hosts=summary["total_hosts"],
            ok_count=summary["ok_count"],
            warning_count=summary["warning_count"],
            critical_count=summary["critical_count"],
            notification_sent=False,
        )
        db.add(report)
        await db.flush()

        for result in host_results:
            detail = HealthCheckDetail(
                report_id=report.id,
                instance=result.get("instance", ""),
                asset_type=result.get("asset_type", "server"),
                host_status=result.get("host_status", "ok"),
                os_info=result.get("os_info", ""),
                kernel_version=result.get("kernel_version", ""),
                cpu_count=result.get("cpu_count"),
                cpu_usage=result.get("cpu_usage"),
                load1=result.get("load1"),
                load5=result.get("load5"),
                load15=result.get("load15"),
                memory_usage=result.get("memory_usage"),
                memory_total_mb=result.get("memory_total_mb"),
                memory_used_mb=result.get("memory_used_mb"),
                disk_usage=result.get("disk_usage"),
                disk_total_gb=result.get("disk_total_gb"),
                is_online=result.get("is_online", True),
                check_details=result.get("check_details", []),
                checked_at=now,
            )
            db.add(detail)

        await db.commit()
        await db.refresh(report)

        logger.info(
            "巡检报告已保存",
            extra={"action": "health_check.run", "report_id": report.id, "total": report.total_hosts, "ok": report.ok_count, "warning": report.warning_count, "critical": report.critical_count},
        )

        return report

    async def _send_feishu_notification(self, report: "HealthCheckReport") -> None:
        """Send feishu card notification for health check report"""
        chat_id = await db_operation_with_retry(
            self._get_notification_chat_id, max_retries=2, retry_delay=1.0
        )

        if not chat_id:
            logger.warning(
                "health_check.chat_id / itreporter_chat_id 未配置，跳过通知",
                extra={"action": "health_check.notify"},
            )
            return

        # Determine overall status and template color
        if report.critical_count > 0:
            overall_status = "严重"
            template = "red"
        elif report.warning_count > 0:
            overall_status = "警告"
            template = "yellow"
        else:
            overall_status = "正常"
            template = "green"

        # Build summary line
        summary_line = (
            f"**巡检概览**：共 {report.total_hosts} 台主机 | "
            f"正常 {report.ok_count} | "
            f"警告 {report.warning_count} | "
            f"严重 {report.critical_count}"
        )

        # Build conclusion
        conclusion = f"**巡检结论**：{overall_status} — "
        if report.critical_count > 0:
            conclusion += f"{report.critical_count} 台主机存在严重问题，需立即处理"
        elif report.warning_count > 0:
            conclusion += f"{report.warning_count} 台主机存在警告，建议关注"
        else:
            conclusion += "所有主机运行正常，无异常"

        elements = []
        elements.append({"tag": "markdown", "content": summary_line})
        elements.append({"tag": "markdown", "content": conclusion})

        # List abnormal hosts with their failed checks
        if report.details:
            abnormal_hosts = [
                d for d in report.details if d.host_status in ("warning", "critical")
            ]
            abnormal_hosts.sort(key=lambda d: (0 if d.host_status == "critical" else 1))
            abnormal_hosts = abnormal_hosts[:3]
            if abnormal_hosts:
                elements.append({"tag": "hr"})
                for detail in abnormal_hosts:
                    status_icon = "🔴" if detail.host_status == "critical" else "⚠️"
                    failed_checks = [
                        c
                        for c in (detail.check_details or [])
                        if c.get("status") in ("warning", "critical")
                    ]
                    check_lines = []
                    for check in failed_checks:
                        check_lines.append(
                            f"  - {check['name']}: {check['value']} (阈值{check['threshold']})"
                        )
                    display_name = detail.instance
                    if detail.asset_type == "terminal" and detail.os_info:
                        display_name = f"{detail.instance} ({detail.os_info})"
                    host_line = f"{status_icon} **{display_name}** ({detail.asset_type})"
                    if check_lines:
                        host_line += "\n" + "\n".join(check_lines)
                    elements.append({"tag": "markdown", "content": host_line})
                total_abnormal = report.warning_count + report.critical_count
                if total_abnormal > 3:
                    elements.append({"tag": "markdown", "content": f"... 共 {total_abnormal} 台异常主机，查看详情了解全部"})

        # Inspection time
        report_time_str = ""
        if report.report_time:
            rt = report.report_time
            if rt.tzinfo is not None:
                rt = rt.astimezone(ZoneInfo("Asia/Shanghai"))
            report_time_str = rt.strftime("%Y-%m-%d %H:%M:%S")
        meta_line = f"巡检时间：{report_time_str}"
        elements.append({"tag": "hr"})
        elements.append({"tag": "markdown", "content": meta_line})

        detail_url = "http://192.168.23.36:8080/ops/health-check"
        elements.append({
            "tag": "button",
            "type": "primary",
            "text": {"tag": "plain_text", "content": "查看详情"},
            "behaviors": [
                {
                    "type": "open_url",
                    "default_url": detail_url,
                    "pc_url": detail_url,
                }
            ],
        })

        feishu_card_message = {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": "每日健康巡检报告"},
                "template": template,
            },
            "body": {"elements": elements},
        }

        feishu_service = get_feishu_service()
        feishu_service.send_message_to_user(
            user_id=chat_id,
            msg_type="interactive",
            content=feishu_card_message,
            receive_id_type="chat_id",
        )

        # Update notification_sent flag
        await db_operation_with_retry(
            lambda db: self._mark_notification_sent(db, report.id),
            max_retries=3, retry_delay=2.0,
        )

        logger.info(f"飞书通知已发送: report_id={report.id}", extra={"action": "health_check.notify", "report_id": report.id, "chat_id": chat_id})

    async def _get_notification_chat_id(self, db):
        from app.config import settings
        from app.crud.crud_system_config import crud_system_config

        chat_id = await crud_system_config.get_value(db, "health_check.chat_id")
        if not chat_id:
            chat_id = await crud_system_config.get_value(db, "itreporter_chat_id")
        if not chat_id:
            chat_id = getattr(settings, "itreporter_chat_id", "")
        return chat_id

    async def _mark_notification_sent(self, db, report_id):
        from app.models.health_check import HealthCheckReport

        result = await db.execute(
            select(HealthCheckReport).where(HealthCheckReport.id == report_id)
        )
        db_report = result.scalar_one_or_none()
        if db_report:
            db_report.notification_sent = True
            await db.commit()

    async def get_latest_report(self) -> "HealthCheckReport | None":
        """Get the latest report from database"""
        return await db_operation_with_retry(
            self._get_latest_report_db, max_retries=2, retry_delay=1.0
        )

    async def _get_latest_report_db(self, db):
        from app.models.health_check import HealthCheckReport

        result = await db.execute(
            select(HealthCheckReport)
            .options(selectinload(HealthCheckReport.details))
            .order_by(HealthCheckReport.report_time.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_report_history(
        self, days: int = 30, page: int = 1, page_size: int = 20
    ) -> tuple[list["HealthCheckReport"], int]:
        """Get report history with pagination"""
        return await db_operation_with_retry(
            lambda db: self._get_report_history_db(db, days, page, page_size),
            max_retries=2, retry_delay=1.0,
        )

    async def _get_report_history_db(self, db, days, page, page_size):
        from app.models.health_check import HealthCheckReport

        since = datetime.now(ZoneInfo("Asia/Shanghai")) - timedelta(days=days)

        query = select(HealthCheckReport).where(
            HealthCheckReport.report_time >= since
        )

        total_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_query)).scalar() or 0

        offset = (page - 1) * page_size
        query = (
            query.order_by(HealthCheckReport.report_time.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        items = list(result.scalars().all())

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_report_by_id(self, report_id: int) -> "HealthCheckReport | None":
        """Get a specific report with its details"""
        return await db_operation_with_retry(
            lambda db: self._get_report_by_id_db(db, report_id),
            max_retries=2, retry_delay=1.0,
        )

    async def _get_report_by_id_db(self, db, report_id):
        from app.models.health_check import HealthCheckReport

        result = await db.execute(
            select(HealthCheckReport)
            .options(selectinload(HealthCheckReport.details))
            .where(HealthCheckReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def export_html_report(self, report_id: int) -> str:
        """Export report as HTML string"""
        report = await self.get_report_by_id(report_id)
        if not report:
            return "<html><body><h1>Report not found</h1></body></html>"

        report_time_str = ""
        if report.report_time:
            rt = report.report_time
            if rt.tzinfo is not None:
                rt = rt.astimezone(ZoneInfo("Asia/Shanghai"))
            report_time_str = rt.strftime("%Y-%m-%d %H:%M:%S")

        # Build summary section
        summary_html = f"""
        <div class="summary">
            <div class="summary-item ok">
                <span class="summary-number">{report.ok_count}</span>
                <span class="summary-label">正常</span>
            </div>
            <div class="summary-item warning">
                <span class="summary-number">{report.warning_count}</span>
                <span class="summary-label">警告</span>
            </div>
            <div class="summary-item critical">
                <span class="summary-number">{report.critical_count}</span>
                <span class="summary-label">严重</span>
            </div>
        </div>"""

        # Build host cards
        host_cards_html = ""
        if report.details:
            for detail in report.details:
                status_class = detail.host_status or "ok"
                status_text = {
                    "ok": "正常",
                    "warning": "警告",
                    "critical": "严重",
                }.get(status_class, "未知")

                check_items_html = ""
                if detail.check_details:
                    for check in detail.check_details:
                        check_status = check.get("status", "ok")
                        check_items_html += f"""
                        <div class="check-item">
                            <div class="check-name">{check.get('name', '')}</div>
                            <div class="check-details">{check.get('value', '')} (阈值{check.get('threshold', '')})</div>
                            <div class="check-status {check_status}">{check_status.upper()}</div>
                        </div>"""

                host_cards_html += f"""
            <div class="host-card">
                <div class="host-name">{detail.instance}</div>
                <div class="host-status {status_class}">{status_text}</div>
                <div class="host-info">
                    <span>类型: {detail.asset_type}</span>
                    <span>OS: {detail.os_info or '-'}</span>
                    <span>内核: {detail.kernel_version or '-'}</span>
                </div>
                <div class="check-list">{check_items_html}</div>
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>健康巡检报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f7fa; color: #333; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 30px 0; border-bottom: 2px solid #e0e0e0; margin-bottom: 20px; }}
        .header h1 {{ font-size: 28px; color: #1a1a1a; }}
        .header .subtitle {{ color: #666; margin-top: 8px; font-size: 14px; }}
        .summary {{ display: flex; justify-content: center; gap: 30px; margin: 30px 0; }}
        .summary-item {{ text-align: center; padding: 20px 30px; border-radius: 8px; min-width: 120px; }}
        .summary-item.ok {{ background: #e8f5e9; border: 1px solid #4caf50; }}
        .summary-item.warning {{ background: #fff8e1; border: 1px solid #ff9800; }}
        .summary-item.critical {{ background: #ffebee; border: 1px solid #f44336; }}
        .summary-number {{ display: block; font-size: 36px; font-weight: bold; }}
        .summary-item.ok .summary-number {{ color: #4caf50; }}
        .summary-item.warning .summary-number {{ color: #ff9800; }}
        .summary-item.critical .summary-number {{ color: #f44336; }}
        .summary-label {{ display: block; font-size: 14px; color: #666; margin-top: 4px; }}
        .host-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 16px; margin: 20px 0; }}
        .host-card {{ background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid #4caf50; }}
        .host-card.warning {{ border-left-color: #ff9800; }}
        .host-card.critical {{ border-left-color: #f44336; }}
        .host-name {{ font-size: 16px; font-weight: bold; margin-bottom: 4px; }}
        .host-status {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; }}
        .host-status.ok {{ background: #e8f5e9; color: #4caf50; }}
        .host-status.warning {{ background: #fff8e1; color: #ff9800; }}
        .host-status.critical {{ background: #ffebee; color: #f44336; }}
        .host-info {{ font-size: 13px; color: #666; margin-bottom: 8px; display: flex; gap: 12px; flex-wrap: wrap; }}
        .check-list {{ border-top: 1px solid #eee; padding-top: 8px; }}
        .check-item {{ display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 13px; }}
        .check-name {{ font-weight: 500; min-width: 80px; }}
        .check-details {{ color: #666; flex: 1; }}
        .check-status {{ padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: bold; }}
        .check-status.ok {{ background: #e8f5e9; color: #4caf50; }}
        .check-status.warning {{ background: #fff8e1; color: #ff9800; }}
        .check-status.critical {{ background: #ffebee; color: #f44336; }}
        .footer {{ text-align: center; padding: 20px 0; color: #999; font-size: 13px; border-top: 1px solid #e0e0e0; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>健康巡检报告</h1>
            <div class="subtitle">共 {report.total_hosts} 台主机</div>
        </div>
        {summary_html}
        <div class="host-grid">
            {host_cards_html}
        </div>
        <div class="footer">
            生成时间: {report_time_str}
        </div>
    </div>
</body>
</html>"""

        return html

    async def export_excel_report(self, report_id: int) -> bytes:
        """Export report as Excel bytes"""
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        report = await self.get_report_by_id(report_id)
        if not report:
            return b""

        wb = Workbook()
        ws = wb.active
        ws.title = "健康巡检报告"

        # Headers
        headers = [
            "IP",
            "资产类型",
            "状态",
            "操作系统",
            "内核版本",
            "CPU核数",
            "CPU使用率(%)",
            "负载1min",
            "负载5min",
            "负载15min",
            "内存使用率(%)",
            "内存总量(MB)",
            "磁盘使用率(%)",
            "磁盘总量(GB)",
            "在线状态",
        ]

        # Header styling
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        # Status fills
        ok_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        warning_fill = PatternFill(start_color="FFF8E1", end_color="FFF8E1", fill_type="solid")
        critical_fill = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")

        # Data rows
        if report.details:
            for row_idx, detail in enumerate(report.details, 2):
                status_text = {
                    "ok": "正常",
                    "warning": "警告",
                    "critical": "严重",
                }.get(detail.host_status, detail.host_status)

                row_data = [
                    detail.instance,
                    detail.asset_type,
                    status_text,
                    detail.os_info or "",
                    detail.kernel_version or "",
                    detail.cpu_count,
                    detail.cpu_usage,
                    detail.load1,
                    detail.load5,
                    detail.load15,
                    detail.memory_usage,
                    detail.memory_total_mb,
                    detail.disk_usage,
                    detail.disk_total_gb,
                    "在线" if detail.is_online else "离线",
                ]

                for col_idx, value in enumerate(row_data, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.alignment = Alignment(horizontal="center", vertical="center")

                    # Color the status column
                    if col_idx == 3:
                        if detail.host_status == "critical":
                            cell.fill = critical_fill
                        elif detail.host_status == "warning":
                            cell.fill = warning_fill
                        else:
                            cell.fill = ok_fill

        # Auto-width columns
        for col_idx in range(1, len(headers) + 1):
            max_length = len(str(headers[col_idx - 1]))
            for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_length + 4, 30)

        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    async def get_thresholds(self) -> dict:
        """Get current thresholds from system_configs"""
        thresholds_value = await db_operation_with_retry(
            self._read_thresholds_value, max_retries=2, retry_delay=1.0
        )

        thresholds = DEFAULT_THRESHOLDS.copy()
        if thresholds_value:
            try:
                custom = json.loads(thresholds_value)
                thresholds.update(custom)
            except (json.JSONDecodeError, TypeError):
                pass

        return thresholds

    async def _read_thresholds_value(self, db):
        from app.crud.crud_system_config import crud_system_config

        return await crud_system_config.get_value(db, "health_check.thresholds")

    async def update_thresholds(self, thresholds: dict) -> dict:
        """Update thresholds in system_configs"""
        merged = DEFAULT_THRESHOLDS.copy()
        merged.update(thresholds)

        await db_operation_with_retry(
            lambda db: self._update_thresholds_db(db, merged),
            max_retries=3, retry_delay=2.0,
        )

        return merged

    async def _update_thresholds_db(self, db, merged):
        from app.crud.crud_system_config import crud_system_config

        existing = await crud_system_config.get_by_key(db, "health_check.thresholds")
        if existing:
            existing.value = json.dumps(merged, ensure_ascii=False)
            await db.commit()
            await db.refresh(existing)
        else:
            await crud_system_config.upsert_by_key(
                db,
                key="health_check.thresholds",
                value=json.dumps(merged, ensure_ascii=False),
                group="health_check",
                description="健康巡检阈值配置",
            )

    async def _ensure_default_thresholds(self, db) -> None:
        """Ensure default thresholds exist in system_configs"""
        from app.crud.crud_system_config import crud_system_config

        existing = await crud_system_config.get_value(db, "health_check.thresholds")
        if not existing:
            await crud_system_config.upsert_by_key(
                db,
                key="health_check.thresholds",
                value=json.dumps(DEFAULT_THRESHOLDS, ensure_ascii=False),
                group="health_check",
                description="健康巡检阈值配置",
            )


health_check_service = HealthCheckService()
