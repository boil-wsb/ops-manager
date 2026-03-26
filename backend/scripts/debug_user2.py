"""
Debug: Check raw user data structure.
"""
import lark_oapi as lark
from lark_oapi.api.contact.v3 import ListScopeRequest, GetUserRequest

APP_ID = "cli_a94a4a8cd3241bd7"
APP_SECRET = "UiYalhbNMevKiES2mD2GGbk4VrahTzUp"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

user_id = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"

get_request = (
    GetUserRequest.builder()
    .user_id(user_id)
    .user_id_type("open_id")
    .build()
)

get_resp = client.contact.v3.user.get(get_request)

print(f"Success: {get_resp.success()}")
print(f"Code: {get_resp.code}")
print(f"Msg: {get_resp.msg}")
print()

if get_resp.data:
    print(f"Data type: {type(get_resp.data)}")
    print(f"Data keys: {get_resp.data.__dict__.keys()}")
    print()

    user = get_resp.data.user
    print(f"User type: {type(user)}")
    print(f"User dict: {user.__dict__ if hasattr(user, '__dict__') else 'N/A'}")
    print()

    print(f"Raw JSON: {lark.JSON.marshal(get_resp.data)}")
