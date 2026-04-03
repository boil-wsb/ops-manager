import asyncio
from app.db.session import get_engine
from sqlalchemy import text

async def check():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND (table_name LIKE '%permission%' OR table_name LIKE '%module%' OR table_name = 'roles')
        """))
        tables = [row[0] for row in result]
        print('Tables with permission/module:', tables)

        result2 = await conn.execute(text("SELECT code, name FROM permissions LIMIT 10"))
        perms = result2.fetchall()
        print('\nExisting permissions (sample):')
        for p in perms:
            print(f'  - {p[0]}: {p[1]}')

if __name__ == "__main__":
    asyncio.run(check())
