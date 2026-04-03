import asyncio
from app.db import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result]
        print("All tables:", tables)
        print("\nAlert/Terminal tables:", [t for t in tables if 'alert' in t or 'terminal' in t])

if __name__ == "__main__":
    asyncio.run(check())
