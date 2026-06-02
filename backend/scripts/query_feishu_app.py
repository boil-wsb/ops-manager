"""
Query Feishu app info and user range.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import lark_oapi as lark

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
USER_ID = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

print("=" * 50)
print("Feishu API Test")
print("=" * 50)
print(f"App ID: {APP_ID}")
print(f"User ID: {USER_ID}")

print("\n" + "-" * 50)
print("Test 1: Send message to user")
print("-" * 50)

try:
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

    request = (
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(USER_ID)
            .msg_type("text")
            .content(lark.JSON.marshal({"text": "Test message"}))
            .build()
        )
        .build()
    )

    resp = client.im.v1.message.create(request)
    if resp.success():
        print(f"SUCCESS: Message sent")
        print(f"Message ID: {resp.data.message_id if resp.data else 'N/A'}")
    else:
        print(f"FAILED: Code={resp.code}, Msg={resp.msg}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 50)
print("Test 2: Query User Info")
print("-" * 50)

try:
    from lark_oapi.api.contact.v3 import GetUserRequest

    request = (
        GetUserRequest.builder()
        .user_id(USER_ID)
        .user_id_type("open_id")
        .build()
    )

    resp = client.contact.v3.user.get(request)
    print(f"Code: {resp.code}, Success: {resp.success()}")

    if resp.success() and resp.data:
        user = resp.data.user
        print(f"Open ID: {getattr(user, 'open_id', 'N/A')}")
        print(f"Union ID: {getattr(user, 'union_id', 'N/A')}")
        print(f"Name: {getattr(user, 'name', 'N/A')}")
        print(f"Email: {getattr(user, 'email', 'N/A')}")
    else:
        print(f"Msg: {resp.msg}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 50)
print("Test 3: List App Scope Users")
print("-" * 50)

try:
    from lark_oapi.api.contact.v3 import ListScopeRequest

    request = ListScopeRequest.builder().user_id_type("open_id").build()
    resp = client.contact.v3.scope.list(request)

    if resp.success() and resp.data:
        user_ids = resp.data.user_ids or []
        print(f"SUCCESS: Found {len(user_ids)} users in app scope")
        for i, uid in enumerate(user_ids, 1):
            print(f"  {i}. {uid}")
    else:
        print(f"FAILED: Code={resp.code}, Msg={resp.msg}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 50)
print("Summary")
print("=" * 50)
print(f"App scope users can receive messages.")
print(f"User {USER_ID} is in scope: {'YES' if USER_ID in (resp.data.user_ids if resp.success() and resp.data else []) else 'NO'}")
