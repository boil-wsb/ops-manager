"""
修复数据库枚举列类型为字符串类型
"""
import asyncio
import asyncpg
from app.config import settings


async def fix_enum_columns():
    """将 source 和 sync_status 列从枚举类型改为字符串类型"""
    # asyncpg 需要 postgresql:// 而不是 postgresql+asyncpg://
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(db_url)

    try:
        print("检查并修复 source 列...")
        # 检查 source 列的类型
        result = await conn.fetchval("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'assets' AND column_name = 'source'
        """)
        print(f"source 列当前类型: {result}")

        if result == 'USER-DEFINED':
            print("需要将 source 列从枚举类型改为字符串类型...")
            # 修改列类型为字符串
            await conn.execute("""
                ALTER TABLE assets
                ALTER COLUMN source TYPE VARCHAR(50)
            """)
            print("source 列已修复")
        else:
            print("source 列已经是字符串类型，无需修复")

        print("\n检查并修复 sync_status 列...")
        # 检查 sync_status 列的类型
        result = await conn.fetchval("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'assets' AND column_name = 'sync_status'
        """)
        print(f"sync_status 列当前类型: {result}")

        if result == 'USER-DEFINED':
            print("需要将 sync_status 列从枚举类型改为字符串类型...")
            # 修改列类型为字符串
            await conn.execute("""
                ALTER TABLE assets
                ALTER COLUMN sync_status TYPE VARCHAR(50)
            """)
            print("sync_status 列已修复")
        else:
            print("sync_status 列已经是字符串类型，无需修复")

        print("\n修复完成！")

    except Exception as e:
        print(f"修复失败: {e}")
        raise
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(fix_enum_columns())
