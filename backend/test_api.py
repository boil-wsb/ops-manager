import asyncio
import sys
sys.path.insert(0, '.')

from app.crud.crud_alert import crud_alert_history
from app.schemas.alert import AlertHistoryResponse
from app.api.deps import get_db

async def test():
    async for db in get_db():
        items, total = await crud_alert_history.get_multi_with_filters(db, skip=0, limit=10)
        print(f'total: {total}, items: {len(items)}')
        if items:
            item = items[0]
            print(f'first item type: {type(item)}')
            validated = AlertHistoryResponse.model_validate(item)
            print(f'validated: OK')
        break

asyncio.run(test())