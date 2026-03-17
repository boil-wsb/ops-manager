"""
修复列的数据类型为 enum 类型
"""
import asyncio
from sqlalchemy import text
from app.db.session import engine


async def fix_column_types():
    async with engine.begin() as conn:
        # 先删除默认值
        await conn.execute(text("""
            ALTER TABLE assets ALTER COLUMN source DROP DEFAULT;
        """))
        await conn.execute(text("""
            ALTER TABLE assets ALTER COLUMN sync_status DROP DEFAULT;
        """))

        # 修改 source 列为 enum 类型
        await conn.execute(text("""
            ALTER TABLE assets 
            ALTER COLUMN source TYPE assetsource 
            USING source::assetsource;
        """))

        # 修改 sync_status 列为 enum 类型
        await conn.execute(text("""
            ALTER TABLE assets 
            ALTER COLUMN sync_status TYPE syncstatus 
            USING sync_status::syncstatus;
        """))

        # 重新设置默认值
        await conn.execute(text("""
            ALTER TABLE assets ALTER COLUMN source SET DEFAULT 'manual';
        """))
        await conn.execute(text("""
            ALTER TABLE assets ALTER COLUMN sync_status SET DEFAULT 'pending';
        """))

        print('Column types fixed successfully')


if __name__ == '__main__':
    asyncio.run(fix_column_types())
