"""
Database initialization script.
Creates default admin user, roles, and permissions.
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import get_async_session_local, get_engine
from app.models.permission import Permission, Role
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_EMAIL = "admin@opsmanager.local"


DEFAULT_PERMISSIONS = [
    {"code": "user:read", "name": "查看用户", "module": "user", "action": "read", "description": "查看用户列表和详情"},
    {"code": "user:create", "name": "创建用户", "module": "user", "action": "create", "description": "创建新用户"},
    {"code": "user:update", "name": "编辑用户", "module": "user", "action": "update", "description": "修改用户信息"},
    {"code": "user:delete", "name": "删除用户", "module": "user", "action": "delete", "description": "删除用户"},
    {"code": "user:assign_role", "name": "分配角色", "module": "user", "action": "execute", "description": "为用户分配角色"},

    {"code": "role:read", "name": "查看角色", "module": "role", "action": "read", "description": "查看角色列表和详情"},
    {"code": "role:create", "name": "创建角色", "module": "role", "action": "create", "description": "创建新角色"},
    {"code": "role:update", "name": "编辑角色", "module": "role", "action": "update", "description": "修改角色信息和权限"},
    {"code": "role:delete", "name": "删除角色", "module": "role", "action": "delete", "description": "删除角色"},

    {"code": "asset:read", "name": "查看资产", "module": "asset", "action": "read", "description": "查看资产列表和详情"},
    {"code": "asset:create", "name": "创建资产", "module": "asset", "action": "create", "description": "创建新资产"},
    {"code": "asset:update", "name": "编辑资产", "module": "asset", "action": "update", "description": "修改资产信息"},
    {"code": "asset:delete", "name": "删除资产", "module": "asset", "action": "delete", "description": "删除资产"},
    {"code": "asset:import", "name": "导入资产", "module": "asset", "action": "execute", "description": "批量导入资产"},
    {"code": "asset:export", "name": "导出资产", "module": "asset", "action": "execute", "description": "导出资产数据"},
    {"code": "asset:admin", "name": "资产管理", "module": "asset", "action": "admin", "description": "管理资产同步等高级操作"},

    {"code": "monitor:read", "name": "查看监控", "module": "monitor", "action": "read", "description": "查看监控项列表和详情"},
    {"code": "monitor:create", "name": "创建监控", "module": "monitor", "action": "create", "description": "创建新监控项"},
    {"code": "monitor:update", "name": "编辑监控", "module": "monitor", "action": "update", "description": "修改监控配置"},
    {"code": "monitor:delete", "name": "删除监控", "module": "monitor", "action": "delete", "description": "删除监控项"},
    {"code": "monitor:test", "name": "测试监控", "module": "monitor", "action": "execute", "description": "手动测试监控项"},

    {"code": "deployment:read", "name": "查看发布", "module": "deployment", "action": "read", "description": "查看发布记录"},
    {"code": "deployment:create", "name": "创建发布", "module": "deployment", "action": "create", "description": "创建新发布记录"},
    {"code": "deployment:approve", "name": "审批发布", "module": "deployment", "action": "execute", "description": "审批发布申请"},
    {"code": "deployment:execute", "name": "执行发布", "module": "deployment", "action": "execute", "description": "执行发布操作"},

    {"code": "ops:read", "name": "查看运维", "module": "ops", "action": "read", "description": "查看运维管理"},
    {"code": "ops:write", "name": "编辑运维", "module": "ops", "action": "write", "description": "编辑运维管理"},
    {"code": "ops:delete", "name": "删除运维", "module": "ops", "action": "delete", "description": "删除运维管理"},

    {"code": "certificate:read", "name": "查看证书", "module": "certificate", "action": "read", "description": "查看证书列表"},
    {"code": "certificate:create", "name": "创建证书", "module": "certificate", "action": "create", "description": "添加新证书"},
    {"code": "certificate:update", "name": "编辑证书", "module": "certificate", "action": "update", "description": "修改证书信息"},
    {"code": "certificate:delete", "name": "删除证书", "module": "certificate", "action": "delete", "description": "删除证书"},
    {"code": "certificate:renew", "name": "续期证书", "module": "certificate", "action": "execute", "description": "证书续期操作"},

    {"code": "setting:read", "name": "查看设置", "module": "setting", "action": "read", "description": "查看系统设置"},
    {"code": "setting:update", "name": "修改设置", "module": "setting", "action": "update", "description": "修改系统配置"},

    {"code": "navigation:read", "name": "查看导航", "module": "navigation", "action": "read", "description": "查看导航链接"},
    {"code": "navigation:create", "name": "创建导航", "module": "navigation", "action": "create", "description": "创建导航链接"},
    {"code": "navigation:update", "name": "编辑导航", "module": "navigation", "action": "update", "description": "修改导航链接"},
    {"code": "navigation:delete", "name": "删除导航", "module": "navigation", "action": "delete", "description": "删除导航链接"},

    {"code": "notification_group:read", "name": "查看通知组", "module": "notification_group", "action": "read", "description": "查看通知组"},
    {"code": "notification_group:create", "name": "创建通知组", "module": "notification_group", "action": "create", "description": "创建通知组"},
    {"code": "notification_group:update", "name": "编辑通知组", "module": "notification_group", "action": "update", "description": "修改通知组"},
    {"code": "notification_group:delete", "name": "删除通知组", "module": "notification_group", "action": "delete", "description": "删除通知组"},
]


DEFAULT_ROLES = {
    "superadmin": {
        "description": "超级管理员",
        "permissions": ["*"],
    },
    "admin": {
        "description": "管理员",
        "permissions": [
            "user:read", "user:create", "user:update", "user:delete", "user:assign_role",
            "role:read", "role:create", "role:update", "role:delete",
            "asset:read", "asset:create", "asset:update", "asset:delete", "asset:import", "asset:export", "asset:admin",
            "monitor:read", "monitor:create", "monitor:update", "monitor:delete", "monitor:test",
            "deployment:read", "deployment:create", "deployment:approve", "deployment:execute",
            "ops:read", "ops:write", "ops:delete",
            "certificate:read", "certificate:create", "certificate:update", "certificate:delete", "certificate:renew",
            "setting:read", "setting:update",
            "navigation:read", "navigation:create", "navigation:update", "navigation:delete",
            "notification_group:read", "notification_group:create", "notification_group:update", "notification_group:delete",
        ],
    },
    "operator": {
        "description": "运维人员",
        "permissions": [
            "asset:read",
            "monitor:read",
            "deployment:read", "deployment:create", "deployment:execute",
            "ops:read",
            "certificate:read",
        ],
    },
    "viewer": {
        "description": "只读用户",
        "permissions": [
            "asset:read",
            "monitor:read",
            "deployment:read",
            "ops:read",
            "certificate:read",
        ],
    },
}


async def create_tables_if_not_exist():
    """Create tables only if they don't exist."""
    from sqlalchemy import inspect

    from app.db.base_class import Base

    async with get_engine().begin() as conn:
        inspector = inspect(conn.sync_connection)
        existing_tables = await conn.run_sync(lambda conn: inspector.get_table_names())
        if not existing_tables:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        else:
            logger.info("Database tables already exist, skipping creation")


async def init_permissions(db: AsyncSession) -> dict:
    """Initialize system permissions."""
    permission_map = {}

    for perm_data in DEFAULT_PERMISSIONS:
        result = await db.execute(
            select(Permission).where(Permission.code == perm_data["code"])
        )
        permission = result.scalar_one_or_none()

        if not permission:
            permission = Permission(**perm_data)
            db.add(permission)
            await db.flush()
            logger.info(f"Created permission: {perm_data['code']}")

        permission_map[perm_data["code"]] = permission.id

    await db.commit()
    logger.info(f"Permissions initialized: {len(permission_map)}")
    return permission_map


async def init_roles(db: AsyncSession, permission_map: dict) -> dict:
    """Initialize system roles using raw SQL to avoid lazy loading issues."""
    role_map = {}

    for role_name, role_data in DEFAULT_ROLES.items():
        result = await db.execute(
            select(Role).where(Role.name == role_name)
        )
        role = result.scalar_one_or_none()

        if not role:
            role = Role(
                name=role_name,
                description=role_data["description"],
                is_system=True,
                is_active=True,
            )
            db.add(role)
            await db.flush()
            logger.info(f"Created role: {role_name}")

        role_map[role_name] = role.id

        await db.execute(
            text("DELETE FROM role_permissions WHERE role_id = :role_id"),
            {"role_id": role.id}
        )

        perm_codes = role_data["permissions"]

        if "*" in perm_codes:
            for perm_id in permission_map.values():
                await db.execute(
                    text("INSERT INTO role_permissions (role_id, permission_id, created_at) VALUES (:role_id, :perm_id, :created_at)"),
                    {"role_id": role.id, "perm_id": perm_id, "created_at": datetime.utcnow()}
                )
        else:
            for code in perm_codes:
                if code in permission_map:
                    perm_id = permission_map[code]
                    await db.execute(
                        text("INSERT INTO role_permissions (role_id, permission_id, created_at) VALUES (:role_id, :perm_id, :created_at)"),
                        {"role_id": role.id, "perm_id": perm_id, "created_at": datetime.utcnow()}
                    )

    await db.commit()
    logger.info(f"Roles initialized: {len(role_map)}")
    return role_map


async def init_admin_user(db: AsyncSession, role_map: dict) -> None:
    """Initialize default admin user using raw SQL."""
    result = await db.execute(
        select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
    )
    admin_user = result.scalar_one_or_none()

    if admin_user:
        logger.info(f"Admin user '{DEFAULT_ADMIN_USERNAME}' already exists")
        return

    superadmin_role_id = role_map.get("superadmin")
    if not superadmin_role_id:
        logger.error("Superadmin role not found")
        return

    admin_user = User(
        username=DEFAULT_ADMIN_USERNAME,
        email=DEFAULT_ADMIN_EMAIL,
        full_name="System Admin",
        hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
        is_active=True,
        is_superuser=True,
    )
    db.add(admin_user)
    await db.flush()

    await db.execute(
        text("INSERT INTO user_roles (user_id, role_id, created_at) VALUES (:user_id, :role_id, :created_at)"),
        {"user_id": admin_user.id, "role_id": superadmin_role_id, "created_at": datetime.utcnow()}
    )

    await db.commit()

    logger.info(f"Created default admin user: {DEFAULT_ADMIN_USERNAME}")
    logger.info(f"Default password: {DEFAULT_ADMIN_PASSWORD}")
    logger.warning("Please change the default password after first login!")


async def check_db_initialized(db: AsyncSession) -> bool:
    """Check if database has been initialized with default data."""
    try:
        result = await db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM users WHERE username = :admin_username) as admin_exists,
                    (SELECT COUNT(*) FROM roles) as role_count,
                    (SELECT COUNT(*) FROM permissions) as perm_count
            """),
            {"admin_username": DEFAULT_ADMIN_USERNAME}
        )
        row = result.one()

        admin_exists = row.admin_exists > 0
        role_count = row.role_count
        perm_count = row.perm_count

        if not admin_exists:
            logger.info("Admin user not found, database needs initialization")
            return False

        if role_count < len(DEFAULT_ROLES):
            logger.info(f"Only {role_count} roles found, expected {len(DEFAULT_ROLES)}")
            return False

        if perm_count < len(DEFAULT_PERMISSIONS):
            logger.info(f"Only {perm_count} permissions found, expected {len(DEFAULT_PERMISSIONS)}")
            return False

        logger.info("Database already initialized with default data")
        logger.info("  - Users: 1 (admin)")
        logger.info(f"  - Roles: {role_count}")
        logger.info(f"  - Permissions: {perm_count}")
        return True

    except Exception as e:
        logger.warning(f"Error checking database state: {e}")
        return False


async def init_db() -> None:
    """Initialize database with default data."""
    logger.info("Checking database initialization...")

    try:
        await create_tables_if_not_exist()
    except Exception as e:
        logger.warning(f"Error creating tables (may already exist): {e}")

    async with await get_async_session_local() as db:
        try:
            if await check_db_initialized(db):
                logger.info("Database already initialized, skipping initialization")
                return

            logger.info("Starting database initialization...")

            permission_map = await init_permissions(db)
            role_map = await init_roles(db, permission_map)
            await init_admin_user(db, role_map)

            logger.info("Database initialization completed successfully!")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(init_db())
