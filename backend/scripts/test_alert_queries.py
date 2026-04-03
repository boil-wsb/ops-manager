import asyncio
from app.db.session import get_engine
from sqlalchemy import text, func

async def test():
    engine = get_engine()
    async with engine.connect() as conn:
        # Test alert_stats endpoint logic
        result = await conn.execute(text("SELECT COUNT(*) FROM alert_history WHERE status = 'firing'"))
        firing = result.scalar()
        print(f"Firing alerts: {firing}")

        result2 = await conn.execute(text("SELECT COUNT(*) FROM alert_receivers"))
        receivers = result2.scalar()
        print(f"Total receivers: {receivers}")

        print("\n✅ Database queries working correctly!")

if __name__ == "__main__":
    asyncio.run(test())
