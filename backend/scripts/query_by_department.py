"""
Query users via find_by_department API.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import lark_oapi as lark
from lark_oapi.api.contact.v3 import FindByDepartmentUserRequest

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

print("=" * 70)
print("Query Users via find_by_department API")
print("=" * 70)

# Try root department
request = (
    FindByDepartmentUserRequest.builder()
    .department_id_type("open_department_id")
    .department_id("0")
    .build()
)

resp = client.contact.v3.user.find_by_department(request)

print(f"\nResult: Code={resp.code}, Success={resp.success()}")
print(f"Msg: {resp.msg}")

if resp.success() and resp.data:
    users = resp.data.items if resp.data.items else []
    print(f"\nFound {len(users)} users in root department\n")

    for i, user in enumerate(users[:10], 1):
        print(f"{i}. {'='*60}")
        print(f"   Open ID:    {getattr(user, 'open_id', 'N/A')}")
        print(f"   Union ID:   {getattr(user, 'union_id', 'N/A')}")
        print(f"   Name:       {getattr(user, 'name', 'N/A')}")
        print(f"   English:    {getattr(user, 'en_name', 'N/A')}")
        print(f"   Email:      {getattr(user, 'email', 'N/A')}")
        print(f"   Mobile:     {getattr(user, 'mobile', 'N/A')}")
        print(f"   Avatar:     {getattr(user, 'avatar_url', 'N/A')}")
else:
    print(f"\nFailed to get users")
