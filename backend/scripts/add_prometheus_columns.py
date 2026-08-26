"""
添加 Prometheus 同步相关字段到 assets 表
"""

import asyncio
from sqlalchemy import text
from app.db.session import engine


async def add_columns():
    async with engine.begin() as conn:
        # Check if columns exist
        result = await conn.execute(
            text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='assets' AND column_name='source'
        """)
        )
        if result.fetchone():
            print("Columns already exist")
            return

        # Add columns
        await conn.execute(text("ALTER TABLE assets ADD COLUMN IF NOT EXISTS arch VARCHAR(50)"))
        await conn.execute(
            text("ALTER TABLE assets ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual'")
        )
        await conn.execute(
            text("ALTER TABLE assets ADD COLUMN IF NOT EXISTS prometheus_instance VARCHAR(255)")
        )
        await conn.execute(
            text(
                "ALTER TABLE assets ADD COLUMN IF NOT EXISTS last_sync_time TIMESTAMP WITH TIME ZONE"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE assets ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending'"
            )
        )

        # Create indexes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_assets_source ON assets(source)"))
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_assets_sync_status ON assets(sync_status)")
        )

        print("Columns added successfully")


if __name__ == "__main__":
    asyncio.run(add_columns())
