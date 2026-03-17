"""
Audit logging constants.
"""


class OperationType:
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REFRESH_TOKEN = "REFRESH_TOKEN"
    CHANGE_PASSWORD = "CHANGE_PASSWORD"
    
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    BATCH_DELETE = "BATCH_DELETE"
    
    ASSIGN_PERMISSION = "ASSIGN_PERMISSION"
    ASSIGN_ROLE = "ASSIGN_ROLE"
    REVOKE_PERMISSION = "REVOKE_PERMISSION"
    REVOKE_ROLE = "REVOKE_ROLE"
    
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"


class Module:
    SYSTEM = "system"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    ASSET = "asset"
    MONITOR = "monitor"
    OPS = "ops"
    CERTIFICATE = "certificate"
