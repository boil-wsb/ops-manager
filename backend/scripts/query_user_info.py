"""
Query user info by open_id from Feishu.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import lark_oapi as lark
from lark_oapi.api.contact.v3 import GetUserRequest

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
USER_ID = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

request = (
    GetUserRequest.builder()
    .user_id(USER_ID)
    .user_id_type("open_id")
    .build()
)

resp = client.contact.v3.user.get(request)

print("=" * 50)
print("Query User Info")
print("=" * 50)
print(f"Success: {resp.success()}")
print(f"Code: {resp.code}")
print(f"Msg: {resp.msg}")

if resp.success() and resp.data:
    print(f"\nRaw response data:")
    print(lark.JSON.marshal(resp.data))
