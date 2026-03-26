"""
Debug: Test ListDepartmentRequest parameters.
"""
import lark_oapi as lark
from lark_oapi.api.contact.v3 import ListDepartmentRequest

APP_ID = "cli_a94a4a8cd3241bd7"
APP_SECRET = "UiYalhbNMevKiES2mD2GGbk4VrahTzUp"

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

# Check available methods
req = ListDepartmentRequest.builder()
print(f"Available methods: {[x for x in dir(req) if not x.startswith('_')]}")

# Try with parent_department_id
req = (
    ListDepartmentRequest.builder()
    .parent_department_id("od-ae83daa6dad4a02ec42a474a319a03ad")
    .department_id_type("open_department_id")
    .build()
)

resp = client.contact.v3.department.list(req)
print(f"Success: {resp.success()}, Code: {resp.code}")
if resp.data and resp.data.items:
    for item in resp.data.items:
        print(f"  Dept: {getattr(item, 'open_department_id', 'N/A')}")
