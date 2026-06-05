"""
Department management API routes.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.logging import get_logger
from app.crud.crud_user import crud_user
from app.models.department import Department
from app.models.user import User

router = APIRouter(prefix="/departments", tags=["部门"])
logger = get_logger(__name__)


def _build_department_tree(
    departments: list[Department],
    users_by_dept: dict[int, list[dict]],
) -> list[dict]:
    """Build a hierarchical department tree from a flat department list.

    Instead of relying on SQLAlchemy recursive selectinload, we manually
    construct the tree by grouping departments by parent_id.

    Args:
        departments: Flat list of all Department ORM objects.
        users_by_dept: Mapping of department_id -> list of user dicts.

    Returns:
        List of root department tree nodes.
    """
    # Build id -> department mapping
    dept_by_id: dict[int, Department] = {d.id: d for d in departments}

    # Build parent_id -> list of child departments mapping
    children_map: dict[int | None, list[Department]] = {}
    for dept in departments:
        children_map.setdefault(dept.parent_id, []).append(dept)

    def _dept_to_dict(dept: Department) -> dict:
        child_depts = children_map.get(dept.id, [])
        children = [_dept_to_dict(child) for child in child_depts]
        dept_users = users_by_dept.get(dept.id, [])
        return {
            "id": dept.id,
            "name": dept.name,
            "feishu_department_id": dept.feishu_department_id,
            "member_count": dept.member_count,
            "is_root": dept.is_root,
            "children": children,
            "users": dept_users,
        }

    # Start from root departments (parent_id is None)
    root_depts = children_map.get(None, [])
    return [_dept_to_dict(d) for d in root_depts]


@router.get("/tree")
async def get_department_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:read"])),
):
    """Get the department tree with users under each department."""
    # Load all departments (flat list)
    result = await db.execute(select(Department))
    departments = list(result.scalars().all())

    # Load all users
    users_result = await db.execute(select(User))
    all_users = users_result.scalars().all()

    # Group users by department_id
    users_by_dept: dict[int, list[dict]] = {}
    for user in all_users:
        if user.department_id:
            dept_users = users_by_dept.setdefault(user.department_id, [])
            dept_users.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "feishu_open_id": user.feishu_open_id,
                "is_active": user.is_active,
            })

    tree = _build_department_tree(departments, users_by_dept)
    return tree


async def _sync_departments_and_users():
    """Internal sync function: sync departments first, then users."""
    from app.db.session import get_async_session_local
    from app.integrations.feishu.sync_service import sync_departments, sync_users

    async with await get_async_session_local() as db:
        dept_result = await sync_departments(db)
        user_result = await sync_users(db, crud_user)
        return {
            "departments": dept_result,
            "users": user_result,
        }


@router.post("/sync")
async def sync_departments_from_feishu(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_permissions(["user:write"])),
):
    """Trigger department + user sync from Feishu.

    Syncs departments first, then users (so user department_id can be resolved).
    Runs in the background and returns immediately.
    """
    background_tasks.add_task(_sync_departments_and_users)

    return {
        "message": "部门及用户同步已在后台启动",
        "status": "pending",
    }
