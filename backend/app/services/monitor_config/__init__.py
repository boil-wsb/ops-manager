"""Prometheus 监控主机配置管理服务。"""

from app.services.monitor_config.monitor_config_service import (
    MonitorConfigService,
    get_monitor_config_service,
)

__all__ = ["MonitorConfigService", "get_monitor_config_service"]
