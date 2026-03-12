"""
Models package.
"""
from app.models.base import BaseModel

# Import all models to ensure proper registration with SQLAlchemy
from app.models.user import User, user_roles
from app.models.permission import Permission, Role, role_permissions
from app.models.asset import Asset, Label, asset_labels
from app.models.monitor import Monitor, Alert, AlertRule, NotificationChannel

__all__ = [
    "BaseModel",
    "User",
    "Role",
    "Permission",
    "Asset",
    "Label",
    "Monitor",
    "Alert",
    "AlertRule",
    "NotificationChannel",
    "user_roles",
    "role_permissions",
    "asset_labels",
]
