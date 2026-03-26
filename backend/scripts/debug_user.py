"""
Query app user scope with full user details - debug version.
"""
import lark_oapi as lark
from lark_oapi.api.contact.v3 import ListScopeRequest, GetUserRequest

APP_ID = "cli_a94a4a8cd3241bd7"
APP_SECRET = "UiYalhbNMevKiES2mD2GGbk4VrahTzUp"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

# Get user IDs in scope
scope_request = ListScopeRequest.builder().user_id_type("open_id").build()
scope_resp = client.contact.v3.scope.list(scope_request)

user_ids = scope_resp.data.user_ids if scope_resp.data else []
print(f"User IDs in scope: {user_ids}\n")

# Try to get first user details
if user_ids:
    user_id = user_ids[0]
    print(f"Querying user: {user_id}\n")

    get_request = (
        GetUserRequest.builder()
        .user_id(user_id)
        .user_id_type("open_id")
        .build()
    )

    get_resp = client.contact.v3.user.get(get_request)

    print(f"Response success: {get_resp.success()}")
    print(f"Response code: {get_resp.code}")
    print(f"Response msg: {get_resp.msg}")

    if get_resp.data:
        print(f"\nRaw data: {lark.JSON.marshal(get_resp.data)}")
        print(f"\nData type: {type(get_resp.data)}")
        print(f"Data dir: {[x for x in dir(get_resp.data) if not x.startswith('_')]}")
