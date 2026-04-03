import asyncio
from datetime import datetime

from app.db.database import async_session_maker
from app.crud.crud_alert import crud_alert_history


async def test_create():
    async with async_session_maker() as db:
        try:
            history = await crud_alert_history.create_from_alertmanager(
                db=db,
                alertname="TestAlert",
                status="firing",
                severity="critical",
                labels={"alertname": "TestAlert", "instance": "192.168.23.36"},
                annotations={"description": "Test alert"},
                starts_at=datetime.utcnow(),
                ends_at=None,
                is_suppressed=False,
                silence_id=None,
            )
            print(f"Success! Created history with id={history.id}, status={history.status}")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")


asyncio.run(test_create())