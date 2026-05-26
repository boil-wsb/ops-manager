"""
Create database tables using SQLAlchemy async API.
This script creates all tables defined in the models.
"""
import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging before any imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import settings first (no model imports)
from app.config import settings

# Import SQLAlchemy components
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Import base model
from app.models.base import BaseModel

# Import models one by one to avoid circular imports
def import_models():
    """Import all models to register them with SQLAlchemy."""
    logger.info("Importing models...")
    
    # Import permission models first (no dependencies on other models)
    from app.models.permission import Permission, Role, role_permissions
    logger.info("  - Permission models imported")
    
    # Import user models (depends on Role)
    from app.models.user import User, user_roles
    logger.info("  - User models imported")
    
    # Import asset models
    from app.models.asset import Asset, Label, asset_labels
    logger.info("  - Asset models imported")
    
    logger.info("All models imported successfully")


async def drop_existing_objects(conn):
    """Drop existing tables and indexes to avoid conflicts."""
    logger.info("\nChecking for existing objects...")
    
    # Drop existing indexes first
    try:
        result = await conn.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'ix_%'
        """))
        indexes = result.fetchall()
        
        for idx in indexes:
            try:
                await conn.execute(text(f'DROP INDEX IF EXISTS "{idx[0]}" CASCADE'))
                logger.info(f"  Dropped index: {idx[0]}")
            except Exception as e:
                logger.warning(f"  Could not drop index {idx[0]}: {e}")
    except Exception as e:
        logger.warning(f"  Could not query indexes: {e}")
    
    # Drop existing tables
    try:
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename DESC
        """))
        tables = result.fetchall()
        
        for table in tables:
            try:
                await conn.execute(text(f'DROP TABLE IF EXISTS "{table[0]}" CASCADE'))
                logger.info(f"  Dropped table: {table[0]}")
            except Exception as e:
                logger.warning(f"  Could not drop table {table[0]}: {e}")
    except Exception as e:
        logger.warning(f"  Could not query tables: {e}")


async def create_tables():
    """Create all database tables."""
    logger.info("=" * 60)
    logger.info("Database Table Creation")
    logger.info("=" * 60)
    logger.info(f"Database URL: {settings.database_url}")
    logger.info("-" * 60)
    
    # Import models
    import_models()
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
    )
    
    try:
        # Drop existing objects and create tables in a transaction
        logger.info("\nSetting up database...")
        async with engine.begin() as conn:
            # Drop existing objects
            await drop_existing_objects(conn)
            
            # Create all tables
            logger.info("\nCreating tables...")
            await conn.run_sync(BaseModel.metadata.create_all)
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ All tables created successfully!")
        logger.info("=" * 60)
        
        # List created tables
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
            )
            tables = result.fetchall()
            logger.info(f"\nCreated {len(tables)} tables:")
            for table in tables:
                logger.info(f"  - {table[0]}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Database initialization complete!")
        logger.info("=" * 60)
                
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error(f"✗ Failed to create tables: {e}")
        logger.error("=" * 60)
        import traceback
        traceback.print_exc()
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(create_tables())
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nFatal error: {e}")
        sys.exit(1)
