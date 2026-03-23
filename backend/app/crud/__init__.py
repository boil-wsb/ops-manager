"""
CRUD operations package.
"""
from app.crud.audit_log import crud_audit_log
from app.crud.base import CRUDBase
from app.crud.crud_asset import crud_asset
from app.crud.crud_pc_client_version import crud_pc_client_version
from app.crud.crud_permission import crud_permission
from app.crud.crud_role import crud_role
from app.crud.crud_user import crud_user

__all__ = [
    "CRUDBase",
    "crud_user",
    "crud_role",
    "crud_permission",
    "crud_asset",
    "crud_audit_log",
    "crud_pc_client_version",
]
