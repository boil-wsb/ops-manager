"""
创建 PostgreSQL enum 类型
"""
import asyncio
from sqlalchemy import text
from app.db.session import engine


async def create_enum_types():
    async with engine.begin() as conn:
        # Create AssetSource enum
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE assetsource AS ENUM ('manual', 'prometheus', 'imported');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))

        # Create SyncStatus enum
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE syncstatus AS ENUM ('pending', 'synced', 'error');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))

        print('Enum types created successfully')


if __name__ == '__main__':
    asyncio.run(create_enum_types())
