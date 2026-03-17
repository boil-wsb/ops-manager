"""
Check existing database tables.
"""
import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_tables():
    """Check existing tables in database."""
    logger.info("=" * 60)
    logger.info("Database Tables Check")
    logger.info("=" * 60)
    
    engine = create_async_engine(settings.database_url, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Get all tables
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
            )
            tables = result.fetchall()
            
            logger.info(f"\nFound {len(tables)} tables:")
            for table in tables:
                logger.info(f"  - {table[0]}")
            
            # Expected tables
            expected_tables = [
                'users', 'roles', 'permissions',
                'user_roles', 'role_permissions',
                'assets', 'labels', 'asset_labels',
                'monitors', 'alerts'
            ]
            
            existing_tables = [t[0] for t in tables]
            missing_tables = [t for t in expected_tables if t not in existing_tables]
            
            if missing_tables:
                logger.info(f"\nMissing tables:")
                for table in missing_tables:
                    logger.info(f"  - {table}")
            else:
                logger.info("\n✓ All expected tables exist!")
            
            # Check if users table has data
            if 'users' in existing_tables:
                result = await conn.execute(text("SELECT COUNT(*) FROM users"))
                count = result.scalar()
                logger.info(f"\nUsers table: {count} records")
            
            # Check if roles table has data
            if 'roles' in existing_tables:
                result = await conn.execute(text("SELECT COUNT(*) FROM roles"))
                count = result.scalar()
                logger.info(f"Roles table: {count} records")
            
            # Check if permissions table has data
            if 'permissions' in existing_tables:
                result = await conn.execute(text("SELECT COUNT(*) FROM permissions"))
                count = result.scalar()
                logger.info(f"Permissions table: {count} records")
                
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_tables())
