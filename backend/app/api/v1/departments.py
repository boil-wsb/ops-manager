"""
Department management API routes.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_permissions
from app.core.logging import get_logger
from app.crud.crud_user import crud_user
from app.models.department import Department
from app.models.user import User

router = APIRouter(prefix="/departments", tags=["部门"])
logger = get_logger(__name__)


class DepartmentLeaderUpdate(BaseModel):
    """Schema for updating department leader."""

    leader_id: int | None = None  # None 表示清除负责人

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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
            "leader_id": dept.leader_id,
            "leader_username": dept.leader.username if dept.leader else None,
            "leader_full_name": dept.leader.full_name if dept.leader else None,
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
    # Load all departments (flat list) with leader preloaded
    result = await db.execute(
        select(Department).options(selectinload(Department.leader))
    )
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
    current_user: User = Depends(require_permissions(["user:update"])),
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


@router.put("/{dept_id}/leader")
async def set_department_leader(
    dept_id: int,
    payload: DepartmentLeaderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:update"])),
):
    """Set or clear the leader of a department.

    - leader_id=None clears the leader.
    - The target user must be active and have a feishu_open_id (required for
      receiving Feishu suggestion cards).
    - Cross-department assignment is allowed (some departments have zero users).
    """
    result = await db.execute(
        select(Department).options(selectinload(Department.leader)).where(Department.id == dept_id)
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")

    leader_id = payload.leader_id

    if leader_id is not None:
        user_result = await db.execute(select(User).where(User.id == leader_id))
        leader = user_result.scalar_one_or_none()
        if not leader or not leader.is_active:
            raise HTTPException(status_code=400, detail="用户不存在或已禁用")
        if not leader.feishu_open_id:
            raise HTTPException(
                status_code=400,
                detail="该用户未绑定飞书账号，无法接收建议卡片",
            )

    dept.leader_id = leader_id
    await db.commit()
    # commit 后 relationship 可能失效，重新查询确保返回最新 leader
    # 根因：db.refresh(dept, attribute_names=["leader"]) 在 commit 后不可靠
    result = await db.execute(
        select(Department).options(selectinload(Department.leader)).where(Department.id == dept_id)
    )
    dept = result.scalar_one()

    logger.info(
        "部门负责人已更新",
        extra={
            "action": "department.set_leader",
            "dept_id": dept.id,
            "dept_name": dept.name,
            "leader_id": leader_id,
            "operator_id": current_user.id,
        },
    )

    return {
        "id": dept.id,
        "name": dept.name,
        "leader_id": dept.leader_id,
        "leader_username": dept.leader.username if dept.leader else None,
        "leader_full_name": dept.leader.full_name if dept.leader else None,
    }
