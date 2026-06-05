"""
Query all users in app scope using combined APIs:
1. list scope - 获取授权范围
2. children department - 递归获取子部门（含部门名称）
3. find_by_department - 获取部门直属用户
4. get - 获取用户详情
"""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import lark_oapi as lark
from lark_oapi.api.contact.v3 import (
    ListScopeRequest,
    ListDepartmentRequest,
    GetDepartmentRequest,
    FindByDepartmentUserRequest,
    GetUserRequest,
)

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

print("=" * 70)
print("Query App Scope Users - With Department Names")
print("=" * 70)

all_user_ids = []
all_department_ids = []
dept_name_map = {}  # dept_id -> dept_name

# Step 1: Get scope
print("\n[Step 1] Get scope info...")
scope_req = ListScopeRequest.builder().user_id_type("open_id").build()
scope_resp = client.contact.v3.scope.list(scope_req)

if scope_resp.success() and scope_resp.data:
    user_ids = scope_resp.data.user_ids or []
    dept_ids = scope_resp.data.department_ids or []

    print(f"  User IDs in scope: {len(user_ids)}")
    print(f"  Department IDs in scope: {len(dept_ids)}")

    all_user_ids.extend(user_ids)
    all_department_ids.extend(dept_ids)
else:
    print(f"  Failed: {scope_resp.msg}")
    exit(1)

# Step 2: Get children departments recursively (with names)
print("\n[Step 2] Get all departments recursively...")

def get_department_name(dept_id):
    """获取部门名称"""
    try:
        req = (
            GetDepartmentRequest.builder()
            .department_id(dept_id)
            .department_id_type("open_department_id")
            .build()
        )
        resp = client.contact.v3.department.get(req)
        if resp.success() and resp.data and resp.data.department:
            return getattr(resp.data.department, 'name', 'N/A') or 'N/A'
    except Exception as e:
        print(f"    Error getting name for dept {dept_id}: {e}")
    return 'N/A'

def get_department_children(dept_id):
    children = []
    try:
        req = (
            ListDepartmentRequest.builder()
            .parent_department_id(dept_id)
            .department_id_type("open_department_id")
            .build()
        )
        resp = client.contact.v3.department.list(req)

        if resp.success() and resp.data and resp.data.items:
            for item in resp.data.items:
                child_id = getattr(item, 'open_department_id', None)
                child_name = getattr(item, 'name', None)
                if child_id:
                    children.append(child_id)
                    if child_name:
                        dept_name_map[child_id] = child_name
                    print(f"    Found child dept: {child_id} ({child_name or 'N/A'})")
    except Exception as e:
        print(f"    Error getting children of {dept_id}: {e}")
    return children

def get_all_departments(dept_ids):
    all_depts = []
    queue = list(dept_ids)

    # 先获取根部门名称
    for dept_id in dept_ids:
        name = get_department_name(dept_id)
        dept_name_map[dept_id] = name
        print(f"    Root dept: {dept_id} ({name})")

    while queue:
        dept_id = queue.pop(0)
        all_depts.append(dept_id)

        children = get_department_children(dept_id)
        for child_id in children:
            if child_id not in all_depts and child_id not in queue:
                queue.append(child_id)

    return all_depts

all_department_ids = get_all_departments(all_department_ids)
print(f"  Total departments found: {len(all_department_ids)}")

# 打印部门列表
print("\n[Department List]")
for i, dept_id in enumerate(all_department_ids, 1):
    name = dept_name_map.get(dept_id, 'N/A')
    print(f"  {i}. {name} ({dept_id})")

# Step 3: Get users from each department
print("\n[Step 3] Get users from each department...")
for dept_id in all_department_ids:
    dept_name = dept_name_map.get(dept_id, 'N/A')
    try:
        req = (
            FindByDepartmentUserRequest.builder()
            .department_id(dept_id)
            .department_id_type("open_department_id")
            .build()
        )
        resp = client.contact.v3.user.find_by_department(req)

        if resp.success() and resp.data and resp.data.items:
            for user in resp.data.items:
                uid = getattr(user, 'open_id', None)
                if uid and uid not in all_user_ids:
                    all_user_ids.append(uid)
            print(f"  {dept_name}: {len(resp.data.items)} users")
        else:
            code = resp.code if resp.code else 0
            if code != 0:
                print(f"  {dept_name}: No permission or empty (code={code})")
            else:
                print(f"  {dept_name}: 0 users")
    except Exception as e:
        print(f"  {dept_name}: Error - {e}")

print(f"\n  Total unique users found: {len(all_user_ids)}")

# Step 4: Get user details
print("\n[Step 4] Get user details...")
print("-" * 70)

for i, uid in enumerate(all_user_ids, 1):
    try:
        req = (
            GetUserRequest.builder()
            .user_id(uid)
            .user_id_type("open_id")
            .build()
        )
        resp = client.contact.v3.user.get(req)

        if resp.success() and resp.data:
            user = resp.data.user
            name = getattr(user, 'name', 'N/A') or 'N/A'
            email = getattr(user, 'email', 'N/A') or 'N/A'
            mobile = getattr(user, 'mobile', 'N/A') or 'N/A'
            dept_ids = getattr(user, 'department_ids', []) or []

            # 将部门 ID 转为部门名称
            dept_names = [dept_name_map.get(did, did) for did in dept_ids]

            print(f"{i}. {name}")
            print(f"   Open ID: {uid}")
            print(f"   Email: {email}")
            print(f"   Mobile: {mobile}")
            print(f"   Departments: {dept_names}")
        else:
            print(f"{i}. {uid} - Failed: {resp.msg}")
    except Exception as e:
        print(f"{i}. {uid} - Error: {e}")

print("\n" + "=" * 70)
print(f"Total users in scope: {len(all_user_ids)}")
