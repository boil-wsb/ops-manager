"""Check database data."""
import asyncio
from app.db.session import async_session_maker
from sqlalchemy import text


async def check_data():
    async with async_session_maker() as session:
        # Check asset count
        result = await session.execute(text('SELECT COUNT(*) FROM assets'))
        asset_count = result.scalar()
        print(f'Assets: {asset_count}')

        # Check monitor count
        result = await session.execute(text('SELECT COUNT(*) FROM monitors'))
        monitor_count = result.scalar()
        print(f'Monitors: {monitor_count}')

        # Check deployment count
        result = await session.execute(text('SELECT COUNT(*) FROM deployments'))
        deployment_count = result.scalar()
        print(f'Deployments: {deployment_count}')

        # Check certificate count
        result = await session.execute(text('SELECT COUNT(*) FROM certificates'))
        cert_count = result.scalar()
        print(f'Certificates: {cert_count}')

        # Check alert count
        result = await session.execute(text('SELECT COUNT(*) FROM alerts'))
        alert_count = result.scalar()
        print(f'Alerts: {alert_count}')


if __name__ == '__main__':
    asyncio.run(check_data())
