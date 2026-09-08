"""One-off: measure raw DB query latency for employee_id lookup."""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.db.session import get_async_session_local


async def main() -> None:
    async with await get_async_session_local() as db:
        for _ in range(3):
            t0 = time.perf_counter()
            r = await db.execute(
                text(
                    "SELECT id, username, employee_id FROM users "
                    "WHERE employee_id = 'ZZ-NOT-EXIST-999' LIMIT 1"
                )
            )
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"SELECT employee_id miss: {elapsed:.1f} ms rows={r.rowcount}")

        # 连接池状态计数
        t0 = time.perf_counter()
        pool = db.get_bind().pool
        print(
            f"pool: size={pool.size()} checkedin={len(pool._checkedin)} "
            f"total_age_ms={((time.perf_counter()-t0)*1000):.1f}"
        )


if __name__ == "__main__":
    asyncio.run(main())