"""
Query Feishu app user scope - Fixed version.
"""
import lark_oapi as lark

APP_ID = "cli_a94a4a8cd3241bd7"
APP_SECRET = "UiYalhbNMevKiES2mD2GGbk4VrahTzUp"
USER_ID = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

print("=" * 60)
print("Query Feishu User Scope - Fixed")
print("=" * 60)

print("\n" + "-" * 60)
print("Method 1: Send message to user (test if in scope)")
print("-" * 60)

try:
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

    request = (
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(USER_ID)
            .msg_type("text")
            .content(lark.JSON.marshal({"text": "Test"}))
            .build()
        )
        .build()
    )

    resp = client.im.v1.message.create(request)
    if resp.success():
        print(f"SUCCESS: Message sent to {USER_ID}")
    else:
        print(f"FAILED: Code={resp.code}, Msg={resp.msg}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 60)
print("Method 2: Get user by open_id")
print("-" * 60)

try:
    from lark_oapi.api.contact.v3 import GetUserRequest

    request = (
        GetUserRequest.builder()
        .user_id(USER_ID)
        .user_id_type("open_id")
        .build()
    )

    resp = client.contact.v3.user.get(request)
    if resp.success():
        print("SUCCESS: User found")
        if resp.data:
            print(f"  Name: {getattr(resp.data, 'name', 'N/A')}")
            print(f"  Open ID: {getattr(resp.data, 'open_id', 'N/A')}")
    else:
        print(f"FAILED: Code={resp.code}")
        print(f"  {resp.msg[:300] if resp.msg else 'N/A'}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 60)
print("Method 3: List users")
print("-" * 60)

try:
    from lark_oapi.api.contact.v3 import ListUserRequest

    request = (
        ListUserRequest.builder()
        .department_id_type("open_department_id")
        .department_id("0")
        .build()
    )

    resp = client.contact.v3.user.list(request)
    if resp.success():
        print("SUCCESS: User list retrieved")
        if resp.data and resp.data.items:
            print(f"Total: {len(resp.data.items)} users")
            for user in resp.data.items[:5]:
                print(f"  - {getattr(user, 'name', 'N/A')} ({getattr(user, 'open_id', 'N/A')})")
    else:
        print(f"FAILED: Code={resp.code}")
        print(f"  {resp.msg[:300] if resp.msg else 'N/A'}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print(f"Error 99992361 = user NOT in app's user scope")
print(f"Error 40004 = no permission to access contact")
print(f"\nIf contact:contact permission is enabled but still fails,")
print(f"check if user is added to app's user range in developer console.")
