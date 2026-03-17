"""
Check database data.
"""
import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_data():
    """Check data in database."""
    logger.info("=" * 60)
    logger.info("Database Data Check")
    logger.info("=" * 60)
    
    engine = create_async_engine(settings.database_url, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Check users
            result = await conn.execute(text("SELECT id, username, email, is_superuser FROM users"))
            users = result.fetchall()
            logger.info(f"\nUsers ({len(users)}):")
            for user in users:
                logger.info(f"  - {user[1]} ({user[2]}), superuser={user[3]}")
            
            # Check roles
            result = await conn.execute(text("SELECT id, name, description, is_system FROM roles"))
            roles = result.fetchall()
            logger.info(f"\nRoles ({len(roles)}):")
            for role in roles:
                logger.info(f"  - {role[1]} ({role[2]}), system={role[3]}")
            
            # Check permissions
            result = await conn.execute(text("SELECT COUNT(*) FROM permissions"))
            count = result.scalar()
            logger.info(f"\nPermissions: {count}")
            
            # Check user_roles
            result = await conn.execute(text("SELECT u.username, r.name FROM user_roles ur JOIN users u ON ur.user_id = u.id JOIN roles r ON ur.role_id = r.id"))
            user_roles = result.fetchall()
            logger.info(f"\nUser-Role assignments ({len(user_roles)}):")
            for ur in user_roles:
                logger.info(f"  - {ur[0]} -> {ur[1]}")
            
            # Check role_permissions
            result = await conn.execute(text("SELECT r.name, COUNT(rp.permission_id) FROM roles r LEFT JOIN role_permissions rp ON r.id = rp.role_id GROUP BY r.id, r.name"))
            role_perms = result.fetchall()
            logger.info(f"\nRole-Permission assignments:")
            for rp in role_perms:
                logger.info(f"  - {rp[0]}: {rp[1]} permissions")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_data())
