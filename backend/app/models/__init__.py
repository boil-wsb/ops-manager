"""
Models package.
"""

from app.models.alert import AlertHistory, AlertSilence, AlertTemplate
from app.models.asset import Asset, Label, asset_labels
from app.models.audit_log import AuditLog
from app.models.base import BaseModel
from app.models.department import Department
from app.models.feishu_interaction import FeishuInteraction
from app.models.health_check import HealthCheckDetail, HealthCheckReport
from app.models.it_feedback import ITFeedback
from app.models.navigation import NavigationLink, navigation_link_roles
from app.models.notification_callback_log import NotificationCallbackLog
from app.models.notification_group import NotificationGroup, notification_group_members
from app.models.notification_record import NotificationRecord
from app.models.ops import Certificate, Deployment, DNSRecord, InspectionReport, InspectionTask
from app.models.pc_client_version import PCClientVersion
from app.models.permission import Permission, Role, role_permissions
from app.models.scheduled_task import ScheduledTask, TaskExecutionLog
from app.models.system_config import SystemConfig
from app.models.terminal_metric import TerminalMetric
from app.models.user import User, user_roles

__all__ = [
    "BaseModel",
    "User",
    "Department",
    "Role",
    "Permission",
    "Asset",
    "Label",
    "AuditLog",
    "NavigationLink",
    "ITFeedback",
    "FeishuInteraction",
    "Deployment",
    "InspectionTask",
    "InspectionReport",
    "Certificate",
    "DNSRecord",
    "PCClientVersion",
    "NotificationGroup",
    "NotificationRecord",
    "NotificationCallbackLog",
    "AlertSilence",
    "AlertTemplate",
    "AlertHistory",
    "TerminalMetric",
    "ScheduledTask",
    "TaskExecutionLog",
    "HealthCheckReport",
    "HealthCheckDetail",
    "SystemConfig",
    "user_roles",
    "role_permissions",
    "asset_labels",
    "navigation_link_roles",
    "notification_group_members",
]
