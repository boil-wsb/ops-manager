"""
测试告警数据
"""
import asyncio
import asyncpg
from app.config import settings


async def check_alerts():
    # asyncpg 需要 postgresql:// 而不是 postgresql+asyncpg://
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(db_url)

    try:
        # 查询告警表
        result = await conn.fetch("""
            SELECT id, title, status, severity, source, monitor_id, created_at
            FROM alerts
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        print(f"\n告警记录 (最近10条):")
        for row in result:
            print(f"  ID: {row['id']}, 标题: {row['title']}, 状态: {row['status']}, 级别: {row['severity']}, 来源: {row['source']}, 监控ID: {row['monitor_id']}")

        
    except Exception as e:
        print(f"查询失败: {e}")
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(check_alerts())
