"""
Query app user scope using ListScope API.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import lark_oapi as lark
from lark_oapi.api.contact.v3 import ListScopeRequest

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

print("=" * 60)
print("Query App User Scope using ListScope API")
print("=" * 60)
print(f"App ID: {APP_ID}")

try:
    request = (
        ListScopeRequest.builder()
        .user_id_type("open_id")
        .build()
    )

    resp = client.contact.v3.scope.list(request)

    print(f"\nResult: Code={resp.code}, Msg={resp.msg}")

    if resp.success() and resp.data:
        print(f"\n" + "-" * 60)
        print(f"Users in App Scope ({len(resp.data.user_ids)} users):")
        print("-" * 60)

        if resp.data.user_ids:
            for i, user_id in enumerate(resp.data.user_ids, 1):
                print(f"  {i}. {user_id}")

        print(f"\n" + "-" * 60)
        print(f"Departments in App Scope:")
        print("-" * 60)

        if resp.data.department_ids:
            for i, dept_id in enumerate(resp.data.department_ids, 1):
                print(f"  {i}. {dept_id}")
        else:
            print("  (No specific departments - may be all employees)")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
