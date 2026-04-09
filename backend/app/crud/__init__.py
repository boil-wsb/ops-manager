"""
CRUD operations package.
"""

from app.crud.audit_log import crud_audit_log
from app.crud.base import CRUDBase
from app.crud.crud_alert import (
    crud_alert_history,
    crud_alert_silence,
    crud_alert_template,
)
from app.crud.crud_asset import crud_asset
from app.crud.crud_notification_record import notification_record
from app.crud.crud_pc_client_version import crud_pc_client_version
from app.crud.crud_permission import crud_permission
from app.crud.crud_role import crud_role
from app.crud.crud_terminal_metric import crud_terminal_metric
from app.crud.crud_user import crud_user

__all__ = [
    "CRUDBase",
    "crud_user",
    "crud_role",
    "crud_permission",
    "crud_asset",
    "crud_audit_log",
    "crud_pc_client_version",
    "crud_alert_silence",
    "crud_alert_template",
    "crud_alert_history",
    "crud_terminal_metric",
    "notification_record",
]
