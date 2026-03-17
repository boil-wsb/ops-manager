"""
Update admin user password.
"""
import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_admin_password():
    """Update admin user password to admin123."""
    logger.info("Updating admin password...")
    
    engine = create_async_engine(settings.database_url, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Generate new password hash
            new_hash = get_password_hash("admin123")
            logger.info(f"New password hash generated: {new_hash[:20]}...")
            
            # Update password
            result = await conn.execute(
                text("UPDATE users SET hashed_password = :password WHERE username = 'admin'"),
                {"password": new_hash}
            )
            await conn.commit()
            
            if result.rowcount > 0:
                logger.info("✓ Admin password updated successfully!")
                logger.info("  Username: admin")
                logger.info("  Password: admin123")
            else:
                logger.warning("Admin user not found!")
                
    except Exception as e:
        logger.error(f"Error updating password: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_admin_password())
