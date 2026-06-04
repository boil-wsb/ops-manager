"""
Feishu user sync service.
"""

from dataclasses import dataclass

from app.config import settings
from app.core.logging import get_logger
from app.core.security import get_password_hash

logger = get_logger(__name__)

DEFAULT_PASSWORD = settings.feishu_sync_default_password

FEISHU_CLIENT: "lark.Client | None" = None  # noqa: F821


def get_lark_module():
    """Lazy import lark_oapi module."""
    import lark_oapi as lark

    return lark


def get_feishu_client() -> "lark.Client":  # noqa: F821
    """Get or create Feishu client."""
    import lark_oapi as lark

    global FEISHU_CLIENT
    if FEISHU_CLIENT is None:
        FEISHU_CLIENT = (
            lark.Client.builder()
            .app_id(settings.feishu_app_id)
            .app_secret(settings.feishu_app_secret)
            .build()
        )
    return FEISHU_CLIENT


@dataclass
class FeishuUser:
    """Feishu user data."""

    open_id: str
    union_id: str | None
    name: str
    enterprise_email: str | None
    email: str | None
    mobile: str | None


def fetch_all_users() -> list[FeishuUser]:
    """Fetch all users from Feishu app scope using combined APIs."""
    from lark_oapi.api.contact.v3 import (
        FindByDepartmentUserRequest,
        GetUserRequest,
        ListDepartmentRequest,
        ListScopeRequest,
    )

    client = get_feishu_client()
    all_user_ids: list[str] = []
    all_department_ids: list[str] = []

    scope_req = ListScopeRequest.builder().user_id_type("open_id").build()
    scope_resp = client.contact.v3.scope.list(scope_req)

    if not scope_resp.success() or not scope_resp.data:
        logger.error(
            f"获取通讯录范围失败: {scope_resp.msg}",
            extra={"action": "feishu.sync", "error": scope_resp.msg},
        )
        return []

    user_ids = scope_resp.data.user_ids or []
    dept_ids = scope_resp.data.department_ids or []

    all_user_ids.extend(user_ids)
    all_department_ids.extend(dept_ids)

    logger.info(
        f"通讯录范围内找到 {len(user_ids)} 个用户和 {len(dept_ids)} 个部门",
        extra={"action": "feishu.sync", "users": len(user_ids), "departments": len(dept_ids)},
    )

    def get_department_children(dept_id: str) -> list[str]:
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
                    child_id = getattr(item, "open_department_id", None)
                    if child_id:
                        children.append(child_id)
        except Exception as e:
            logger.error(
                f"获取子部门失败: {dept_id}",
                extra={"action": "feishu.sync", "dept_id": dept_id, "error": str(e)},
            )
        return children

    queue = list(all_department_ids)
    while queue:
        dept_id = queue.pop(0)
        children = get_department_children(dept_id)
        for child_id in children:
            if child_id not in all_department_ids and child_id not in queue:
                queue.append(child_id)
                all_department_ids.append(child_id)

    logger.info(
        f"共找到 {len(all_department_ids)} 个部门",
        extra={"action": "feishu.sync", "total_departments": len(all_department_ids)},
    )

    for dept_id in all_department_ids:
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
                    uid = getattr(user, "open_id", None)
                    if uid and uid not in all_user_ids:
                        all_user_ids.append(uid)
        except Exception as e:
            logger.error(
                f"获取部门用户失败: {dept_id}",
                extra={"action": "feishu.sync", "dept_id": dept_id, "error": str(e)},
            )

    logger.info(
        f"共找到 {len(all_user_ids)} 个用户",
        extra={"action": "feishu.sync", "total_users": len(all_user_ids)},
    )

    users = []
    for uid in all_user_ids:
        try:
            req = GetUserRequest.builder().user_id(uid).user_id_type("open_id").build()
            resp = client.contact.v3.user.get(req)

            if resp.success() and resp.data and resp.data.user:
                user = resp.data.user
                feishu_user = FeishuUser(
                    open_id=getattr(user, "open_id", uid) or uid,
                    union_id=getattr(user, "union_id", None),
                    name=getattr(user, "name", None) or "Unknown",
                    enterprise_email=getattr(user, "enterprise_email", None),
                    email=getattr(user, "email", None),
                    mobile=getattr(user, "mobile", None),
                )
                users.append(feishu_user)
        except Exception as e:
            logger.error(
                f"获取用户详情失败: {uid}",
                extra={"action": "feishu.sync", "uid": uid, "error": str(e)},
            )

    logger.info(
        f"获取到 {len(users)} 个用户详情", extra={"action": "feishu.sync", "users": len(users)}
    )
    return users


async def sync_users(db, crud_user) -> dict:
    """Sync Feishu users to local database (incremental sync)."""
    feishu_users = fetch_all_users()

    if not feishu_users:
        return {
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "errors": ["No users fetched from Feishu"],
        }

    feishu_open_ids = {u.open_id for u in feishu_users}

    existing_users = await crud_user.get_all_feishu_users(db)
    existing_map = {u.feishu_open_id: u for u in existing_users if u.feishu_open_id}

    created = 0
    updated = 0
    deleted = 0
    errors = []

    for feishu_user in feishu_users:
        try:
            if feishu_user.open_id in existing_map:
                existing_user = existing_map[feishu_user.open_id]

                need_update = False
                if feishu_user.name and existing_user.full_name != feishu_user.name:
                    existing_user.full_name = feishu_user.name
                    need_update = True
                if (
                    feishu_user.enterprise_email
                    and existing_user.email != feishu_user.enterprise_email
                ):
                    existing_user.email = feishu_user.enterprise_email
                    need_update = True

                if need_update:
                    await crud_user.update_feishu_user(
                        db,
                        user=existing_user,
                        full_name=feishu_user.name,
                        email=feishu_user.enterprise_email,
                        mobile=feishu_user.mobile,
                    )
                    updated += 1
            else:
                username = (
                    feishu_user.enterprise_email.split("@")[0]
                    if feishu_user.enterprise_email
                    else feishu_user.open_id
                )

                check_email = (
                    await crud_user.get_by_email(db, email=feishu_user.enterprise_email)
                    if feishu_user.enterprise_email
                    else None
                )
                if check_email and check_email.feishu_open_id != feishu_user.open_id:
                    logger.warning(
                        f"企业邮箱已存在: {feishu_user.enterprise_email}, 使用open_id作为用户名",
                        extra={"action": "feishu.sync", "email": feishu_user.enterprise_email},
                    )
                    username = feishu_user.open_id

                await crud_user.create_feishu_user(
                    db,
                    feishu_open_id=feishu_user.open_id,
                    feishu_union_id=feishu_user.union_id,
                    username=username,
                    full_name=feishu_user.name,
                    email=feishu_user.enterprise_email if feishu_user.enterprise_email else None,
                    mobile=feishu_user.mobile,
                    hashed_password=get_password_hash(DEFAULT_PASSWORD),
                )
                created += 1
        except Exception as e:
            logger.error(
                f"同步用户失败: {feishu_user.open_id}",
                extra={"action": "feishu.sync", "open_id": feishu_user.open_id, "error": str(e)},
            )
            errors.append(f"User {feishu_user.open_id}: {str(e)}")

    local_feishu_open_ids = set(existing_map.keys())
    users_to_delete = local_feishu_open_ids - feishu_open_ids

    for open_id in users_to_delete:
        try:
            user = existing_map[open_id]
            await crud_user.delete_feishu_user(db, user=user)
            deleted += 1
        except Exception as e:
            logger.error(
                f"删除用户失败: {open_id}",
                extra={"action": "feishu.sync", "open_id": open_id, "error": str(e)},
            )
            errors.append(f"Delete {open_id}: {str(e)}")

    result = {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "total_feishu": len(feishu_users),
        "errors": errors if errors else None,
    }

    logger.info(
        "飞书同步完成",
        extra={
            "action": "feishu.sync",
            "created_count": created,
            "updated_count": updated,
            "deleted_count": deleted,
            "total_feishu": len(feishu_users),
        },
    )
    return result
