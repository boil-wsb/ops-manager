"""
Database initialization script.
Creates default admin user, roles, and permissions.
"""
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session
from app.models.permission import Permission, Role
from app.models.user import User
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Default admin user credentials
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_EMAIL = "admin@opsmanager.local"


# System preset permissions
DEFAULT_PERMISSIONS = [
    # User management
    {"code": "user:read", "name": "查看用户", "module": "user", "action": "read", "description": "查看用户列表和详情"},
    {"code": "user:create", "name": "创建用户", "module": "user", "action": "create", "description": "创建新用户"},
    {"code": "user:update", "name": "编辑用户", "module": "user", "action": "update", "description": "修改用户信息"},
    {"code": "user:delete", "name": "删除用户", "module": "user", "action": "delete", "description": "删除用户"},
    {"code": "user:assign_role", "name": "分配角色", "module": "user", "action": "execute", "description": "为用户分配角色"},
    
    # Role management
    {"code": "role:read", "name": "查看角色", "module": "role", "action": "read", "description": "查看角色列表和详情"},
    {"code": "role:create", "name": "创建角色", "module": "role", "action": "create", "description": "创建新角色"},
    {"code": "role:update", "name": "编辑角色", "module": "role", "action": "update", "description": "修改角色信息和权限"},
    {"code": "role:delete", "name": "删除角色", "module": "role", "action": "delete", "description": "删除角色"},
    
    # Asset management
    {"code": "asset:read", "name": "查看资产", "module": "asset", "action": "read", "description": "查看资产列表和详情"},
    {"code": "asset:create", "name": "创建资产", "module": "asset", "action": "create", "description": "创建新资产"},
    {"code": "asset:update", "name": "编辑资产", "module": "asset", "action": "update", "description": "修改资产信息"},
    {"code": "asset:delete", "name": "删除资产", "module": "asset", "action": "delete", "description": "删除资产"},
    {"code": "asset:import", "name": "导入资产", "module": "asset", "action": "execute", "description": "批量导入资产"},
    {"code": "asset:export", "name": "导出资产", "module": "asset", "action": "execute", "description": "导出资产数据"},
    
    # Monitor management
    {"code": "monitor:read", "name": "查看监控", "module": "monitor", "action": "read", "description": "查看监控项列表和详情"},
    {"code": "monitor:create", "name": "创建监控", "module": "monitor", "action": "create", "description": "创建新监控项"},
    {"code": "monitor:update", "name": "编辑监控", "module": "monitor", "action": "update", "description": "修改监控配置"},
    {"code": "monitor:delete", "name": "删除监控", "module": "monitor", "action": "delete", "description": "删除监控项"},
    {"code": "monitor:test", "name": "测试监控", "module": "monitor", "action": "execute", "description": "手动测试监控项"},
    
    # Alert management
    {"code": "alert:read", "name": "查看告警", "module": "alert", "action": "read", "description": "查看告警事件"},
    {"code": "alert:acknowledge", "name": "确认告警", "module": "alert", "action": "execute", "description": "确认告警事件"},
    {"code": "alert:resolve", "name": "解决告警", "module": "alert", "action": "execute", "description": "标记告警为已解决"},
    {"code": "alert:delete", "name": "删除告警", "module": "alert", "action": "delete", "description": "删除告警记录"},
    
    # Deployment management
    {"code": "deployment:read", "name": "查看发布", "module": "deployment", "action": "read", "description": "查看发布记录"},
    {"code": "deployment:create", "name": "创建发布", "module": "deployment", "action": "create", "description": "创建新发布记录"},
    {"code": "deployment:approve", "name": "审批发布", "module": "deployment", "action": "execute", "description": "审批发布申请"},
    {"code": "deployment:execute", "name": "执行发布", "module": "deployment", "action": "execute", "description": "执行发布操作"},
    
    # Certificate management
    {"code": "certificate:read", "name": "查看证书", "module": "certificate", "action": "read", "description": "查看证书列表"},
    {"code": "certificate:create", "name": "创建证书", "module": "certificate", "action": "create", "description": "添加新证书"},
    {"code": "certificate:update", "name": "编辑证书", "module": "certificate", "action": "update", "description": "修改证书信息"},
    {"code": "certificate:delete", "name": "删除证书", "module": "certificate", "action": "delete", "description": "删除证书"},
    {"code": "certificate:renew", "name": "续期证书", "module": "certificate", "action": "execute", "description": "证书续期操作"},
    
    # System settings
    {"code": "setting:read", "name": "查看设置", "module": "setting", "action": "read", "description": "查看系统设置"},
    {"code": "setting:update", "name": "修改设置", "module": "setting", "action": "update", "description": "修改系统配置"},
]


# System preset roles with permission codes
DEFAULT_ROLES = {
    "superadmin": {
        "description": "超级管理员",
        "permissions": ["*"],  # All permissions
    },
    "admin": {
        "description": "管理员",
        "permissions": [
            "user:read", "user:create", "user:update", "user:delete", "user:assign_role",
            "role:read", "role:create", "role:update", "role:delete",
            "asset:read", "asset:create", "asset:update", "asset:delete", "asset:import", "asset:export",
            "monitor:read", "monitor:create", "monitor:update", "monitor:delete", "monitor:test",
            "alert:read", "alert:acknowledge", "alert:resolve", "alert:delete",
            "deployment:read", "deployment:create", "deployment:approve", "deployment:execute",
            "certificate:read", "certificate:create", "certificate:update", "certificate:delete", "certificate:renew",
            "setting:read", "setting:update",
        ],
    },
    "operator": {
        "description": "运维人员",
        "permissions": [
            "asset:read",
            "monitor:read",
            "alert:read", "alert:acknowledge", "alert:resolve",
            "deployment:read", "deployment:create", "deployment:execute",
            "certificate:read",
        ],
    },
    "viewer": {
        "description": "只读用户",
        "permissions": [
            "asset:read",
            "monitor:read",
            "alert:read",
            "deployment:read",
            "certificate:read",
        ],
    },
}


async def init_permissions(db: AsyncSession) -> dict:
    """Initialize system permissions."""
    from sqlalchemy import select
    
    permission_map = {}
    
    for perm_data in DEFAULT_PERMISSIONS:
        # Check if permission exists
        result = await db.execute(
            select(Permission).where(Permission.code == perm_data["code"])
        )
        permission = result.scalar_one_or_none()
        
        if not permission:
            # Create permission
            permission = Permission(**perm_data)
            db.add(permission)
            await db.flush()
            logger.info(f"Created permission: {perm_data['code']}")
        
        permission_map[perm_data["code"]] = permission
    
    await db.commit()
    logger.info(f"Permissions initialized: {len(permission_map)}")
    return permission_map


async def init_roles(db: AsyncSession, permission_map: dict) -> dict:
    """Initialize system roles."""
    from sqlalchemy import select
    
    role_map = {}
    
    for role_name, role_data in DEFAULT_ROLES.items():
        # Check if role exists
        result = await db.execute(
            select(Role).where(Role.name == role_name)
        )
        role = result.scalar_one_or_none()
        
        if not role:
            # Create role
            role = Role(
                name=role_name,
                description=role_data["description"],
                is_system=True,
                is_active=True,
            )
            db.add(role)
            await db.flush()
            logger.info(f"Created role: {role_name}")
        
        # Update role permissions
        role.permissions = []
        perm_codes = role_data["permissions"]
        
        if "*" in perm_codes:
            # Superadmin gets all permissions
            role.permissions = list(permission_map.values())
        else:
            for code in perm_codes:
                if code in permission_map:
                    role.permissions.append(permission_map[code])
        
        role_map[role_name] = role
    
    await db.commit()
    logger.info(f"Roles initialized: {len(role_map)}")
    return role_map


async def init_admin_user(db: AsyncSession, role_map: dict) -> None:
    """Initialize default admin user."""
    from sqlalchemy import select
    
    # Check if admin user exists
    result = await db.execute(
        select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
    )
    admin_user = result.scalar_one_or_none()
    
    if admin_user:
        logger.info(f"Admin user '{DEFAULT_ADMIN_USERNAME}' already exists")
        return
    
    # Get superadmin role
    superadmin_role = role_map.get("superadmin")
    if not superadmin_role:
        logger.error("Superadmin role not found")
        return
    
    # Create admin user
    admin_user = User(
        username=DEFAULT_ADMIN_USERNAME,
        email=DEFAULT_ADMIN_EMAIL,
        full_name="系统管理员",
        hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
        is_active=True,
        is_superuser=True,
    )
    admin_user.roles.append(superadmin_role)
    
    db.add(admin_user)
    await db.commit()
    
    logger.info(f"Created default admin user: {DEFAULT_ADMIN_USERNAME}")
    logger.info(f"Default password: {DEFAULT_ADMIN_PASSWORD}")
    logger.warning("Please change the default password after first login!")


async def init_db() -> None:
    """Initialize database with default data."""
    logger.info("Initializing database...")
    
    async with async_session() as db:
        try:
            # Initialize permissions
            permission_map = await init_permissions(db)
            
            # Initialize roles
            role_map = await init_roles(db, permission_map)
            
            # Initialize admin user
            await init_admin_user(db, role_map)
            
            logger.info("Database initialization completed successfully!")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(init_db())
