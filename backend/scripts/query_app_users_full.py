"""
Query app user scope with full user details.
"""
import lark_oapi as lark
from lark_oapi.api.contact.v3 import ListScopeRequest, GetUserRequest

APP_ID = "cli_a94a4a8cd3241bd7"
APP_SECRET = "UiYalhbNMevKiES2mD2GGbk4VrahTzUp"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

print("=" * 70)
print("Query App User Scope - Full User Details")
print("=" * 70)

# Get user IDs in scope
scope_request = ListScopeRequest.builder().user_id_type("open_id").build()
scope_resp = client.contact.v3.scope.list(scope_request)

user_ids = scope_resp.data.user_ids if scope_resp.data else []
print(f"\nFound {len(user_ids)} users in app scope\n")

if not user_ids:
    print("No users in scope")
    exit(0)

# Query each user individually
for i, user_id in enumerate(user_ids, 1):
    get_request = (
        GetUserRequest.builder()
        .user_id(user_id)
        .user_id_type("open_id")
        .build()
    )

    get_resp = client.contact.v3.user.get(get_request)

    if get_resp.success() and get_resp.data:
        user = get_resp.data.user  # Access nested user object

        print(f"{i}. {'='*60}")
        print(f"   Open ID:    {getattr(user, 'open_id', 'N/A')}")
        print(f"   Union ID:   {getattr(user, 'union_id', 'N/A')}")
        print(f"   Name:       {getattr(user, 'name', 'N/A')}")
        print(f"   English:    {getattr(user, 'en_name', 'N/A')}")
        print(f"   Email:      {getattr(user, 'email', 'N/A')}")
        print(f"   Mobile:     {getattr(user, 'mobile', 'N/A')}")
        print(f"   Avatar:     {getattr(user, 'avatar_url', 'N/A')}")
    else:
        print(f"{i}. {user_id} - Failed: {get_resp.msg}")
