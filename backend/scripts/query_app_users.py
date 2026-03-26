"""
Query users in app scope using various methods.
"""
import lark_oapi as lark

APP_ID = "cli_a94a4a8cd3241bd7"
APP_SECRET = "UiYalhbNMevKiES2mD2GGbk4VrahTzUp"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

print("=" * 60)
print("Query Users in App Scope - Methods")
print("=" * 60)

print("\n" + "-" * 60)
print("Method 1: Check SDK contact.v3 module structure")
print("-" * 60)

try:
    print(f"  dir(lark.contact.v3): {[x for x in dir(lark.contact.v3) if not x.startswith('_')]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 60)
print("Method 2: Check contact.v3.service structure")
print("-" * 60)

try:
    if hasattr(lark.contact.v3, 'service'):
        print(f"  dir(lark.contact.v3.service): {[x for x in dir(lark.contact.v3.service) if not x.startswith('_')]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 60)
print("Method 3: Try BatchGetIdUserRequest")
print("-" * 60)

try:
    from lark_oapi.api.contact.v3 import BatchGetIdUserRequest

    print(f"  dir(BatchGetIdUserRequest): {[x for x in dir(BatchGetIdUserRequest) if not x.startswith('_')]}")

    req = BatchGetIdUserRequest.builder()
    print(f"  Builder methods: {[x for x in dir(req) if not x.startswith('_') and 'user' in x.lower()]}")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 60)
print("Method 4: Try to get user by union_id (more reliable)")
print("-" * 60)

union_id = "on_7db1c3692f472f2cee2c80b84f918488"

try:
    from lark_oapi.api.contact.v3 import GetUserRequest

    request = (
        GetUserRequest.builder()
        .user_id(union_id)
        .user_id_type("union_id")
        .build()
    )

    resp = client.contact.v3.user.get(request)
    print(f"  Get by union_id: Code={resp.code}, Success={resp.success()}")
    if resp.success():
        print(f"  Name: {getattr(resp.data, 'name', 'N/A')}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 60)
print("Method 5: List users via department (if dept visible)")
print("-" * 60)

try:
    from lark_oapi.api.contact.v3 import ListUserRequest

    request = (
        ListUserRequest.builder()
        .department_id_type("open_department_id")
        .department_id("0")
        .page_size(10)
        .build()
    )

    resp = client.contact.v3.user.list(request)
    print(f"  List users: Code={resp.code}, Success={resp.success()}")
    if resp.success() and resp.data:
        print(f"  Total: {len(resp.data.items) if resp.data.items else 0}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 60)
print("Summary")
print("-" * 60)
print("  The app has limited contact permissions (error 40004).")
print("  To query full user list, need to enable 'contact:contact:readonly'")
print("  permission and add users to app scope in developer console.")
