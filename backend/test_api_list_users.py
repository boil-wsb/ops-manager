"""
Test API endpoint for user list.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from app.core.security import create_access_token


async def test_api_list_users():
    """Test user list via API."""
    print("=" * 60)
    print("Testing User List API")
    print("=" * 60)
    
    # Create a test token for admin user
    token = create_access_token(
        data={"sub": "1", "type": "access"}  # admin user id
    )
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0) as client:
        print(f"\nSending GET /api/v1/users")
        
        try:
            response = await client.get(
                "/api/v1/users",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ API call successful!")
                print(f"  Code: {data.get('code')}")
                print(f"  Message: {data.get('message')}")
                items = data.get('data', {}).get('items', [])
                print(f"  Users count: {len(items)}")
                for u in items[:3]:
                    print(f"    - {u.get('username')} (ID: {u.get('id')})")
            else:
                print(f"\n❌ API request failed with status {response.status_code}")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_api_list_users())
