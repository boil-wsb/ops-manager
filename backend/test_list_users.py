"""
Test script to verify user list API.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import async_session
from app.crud.crud_user import crud_user


async def test_list_users():
    """Test user list."""
    print("=" * 60)
    print("Testing User List")
    print("=" * 60)
    
    async with async_session() as db:
        try:
            users = await crud_user.get_multi(db)
            print(f"\n✅ Users count: {len(users)}")
            for u in users:
                print(f"  - {u.username} (ID: {u.id})")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_list_users())
