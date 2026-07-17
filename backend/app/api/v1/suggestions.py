"""
Anonymous suggestion API endpoints.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_permissions
from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.models.department import Department
from app.models.suggestion import Suggestion, SuggestionAssignment, SuggestionStatus
from app.models.user import User
from app.schemas.suggestion import (
    AssignmentResponse,
    SuggestionArchiveIn,
    SuggestionCreate,
    SuggestionListResponse,
    SuggestionResponse,
    SuggestionSubmitResponse,
    SuggestionTrackResponse,
)
from app.services.suggestion_service import (
    generate_query_code,
    get_client_ip,
    send_pending_card,
    status_text,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/suggestions", tags=["匿名建议"])


def _build_assignment_response(a: SuggestionAssignment) -> AssignmentResponse:
    return AssignmentResponse(
        id=a.id,
        suggestion_id=a.suggestion_id,
        department_id=a.department_id,
        department_name=a.department.name if a.department else None,
        assignee_user_id=a.assignee_user_id,
        assignee_name=(
            a.assignee_user.full_name or a.assignee_user.username
            if a.assignee_user
            else None
        ),
        assignee_open_id=a.assignee_open_id,
        open_message_id=a.open_message_id,
        status=a.status,
        reviewed_at=a.reviewed_at,
        review_comment=a.review_comment,
    )


def _build_suggestion_response(s: Suggestion) -> SuggestionResponse:
    return SuggestionResponse(
        id=s.id,
        content=s.content,
        highlights=s.highlights,
        innovation_ideas=s.innovation_ideas,
        status=s.status,
        query_code=s.query_code,
        market_result=s.market_result,
        archived_at=s.archived_at,
        reject_reason=s.reject_reason,
        rejected_at=s.rejected_at,
        created_at=s.created_at,
        assignments=[_build_assignment_response(a) for a in s.assignments],
    )


async def _send_cards_task(
    suggestion_id: int,
    content: str,
    highlights: str | None,
    innovation_ideas: str | None,
    dept_names: str,
    assignments: list[dict],
) -> None:
    """Background task: send pending cards to all recipients and update open_message_id."""
    from app.db.session import get_async_session_local

    async with await get_async_session_local() as db:
        for a_info in assignments:
            open_id = a_info.get("assignee_open_id")
            assignment_id = a_info.get("assignment_id")
            if not open_id or not assignment_id:
                continue
            msg_id = await send_pending_card(
                open_id=open_id,
                suggestion_id=suggestion_id,
                assignment_id=assignment_id,
                content=content,
                highlights=highlights,
                innovation_ideas=innovation_ideas,
                dept_names=dept_names,
            )
            if msg_id:
                result = await db.execute(
                    select(SuggestionAssignment).where(SuggestionAssignment.id == assignment_id)
                )
                assignment = result.scalar_one_or_none()
                if assignment:
                    assignment.open_message_id = msg_id
                    await db.commit()
                    logger.info(
                        f"Updated assignment open_message_id: assignment={assignment_id}, msg_id={msg_id}",
                        extra={"action": "suggestion.submit", "assignment_id": assignment_id, "message_id": msg_id},
                    )


@router.post("", response_model=SuggestionSubmitResponse)
async def submit_suggestion(
    data: SuggestionCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["suggestion:submit"])),
):
    """提交匿名建议。

    记录 submitter_id 用于审计但不返回给客户端。
    向部门负责人/指派人发送飞书审批卡片。
    """
    if not data.department_id and not data.assignee_user_id:
        raise HTTPException(status_code=400, detail="请至少选择一个指派部门或指派人")

    # 1. 生成查询码 + 保存建议
    # I-06 修复：捕获 IntegrityError（query_code unique 约束冲突）后重新生成 code 并重试。
    # 根因：generate_query_code 的 SELECT 查重存在 TOCTOU 竞态，两个并发提交可能同时
    # SELECT 返回 None，然后 INSERT 同一 code。DB 层 unique 约束会拒绝第二个 INSERT，
    # 调用方捕获异常后重新生成 code 即可。
    max_code_retries = 3
    suggestion: Suggestion | None = None
    for attempt in range(1, max_code_retries + 1):
        query_code = await generate_query_code(db)
        suggestion = Suggestion(
            content=data.content,
            highlights=data.highlights,
            innovation_ideas=data.innovation_ideas,
            status=SuggestionStatus.PENDING,
            query_code=query_code,
            submitter_id=current_user.id,
            client_ip=get_client_ip(request),
        )
        db.add(suggestion)
        try:
            await db.flush()  # 获取 suggestion.id
            break  # 成功，跳出重试循环
        except IntegrityError as e:
            await db.rollback()
            if attempt < max_code_retries:
                logger.warning(
                    f"query_code unique 冲突，重试 (attempt {attempt}/{max_code_retries}): "
                    f"code={query_code}, error={e}",
                    extra={
                        "action": "suggestion.submit",
                        "retry_attempt": attempt,
                        "query_code": query_code,
                    },
                )
            else:
                logger.error(
                    f"query_code unique 冲突，重试 {max_code_retries} 次后仍失败: code={query_code}",
                    extra={
                        "action": "suggestion.submit",
                        "retry_exhausted": True,
                        "query_code": query_code,
                    },
                )
                raise HTTPException(status_code=500, detail="生成查询码失败，请重试") from e

    if suggestion is None or suggestion.id is None:
        raise HTTPException(status_code=500, detail="生成查询码失败")

    # 3. 收集接收人: 部门负责人 + 指派人
    recipients: list[dict] = []  # [{assignee_open_id, department_id, assignee_user_id, assignment_id}]
    seen_open_ids: set[str] = set()

    # 3a. 部门负责人（单选）
    dept_names = ""
    if data.department_id:
        dept_result = await db.execute(
            select(Department).where(Department.id == data.department_id)
        )
        dept = dept_result.scalar_one_or_none()
        if dept and dept.leader_id and dept.leader and dept.leader.feishu_open_id:
            dept_names = dept.name
            open_id = dept.leader.feishu_open_id
            seen_open_ids.add(open_id)
            assignment = SuggestionAssignment(
                suggestion_id=suggestion.id,
                department_id=dept.id,
                assignee_user_id=dept.leader_id,
                assignee_open_id=open_id,
                status="pending",
            )
            db.add(assignment)
            await db.flush()
            recipients.append({
                "assignee_open_id": open_id,
                "assignment_id": assignment.id,
            })
        else:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail="所选部门未配置负责人或负责人无飞书 open_id,无法发送审批卡片",
            )

    # 3b. 指派人（单选）
    if data.assignee_user_id:
        user_result = await db.execute(
            select(User).where(User.id == data.assignee_user_id, User.is_active.is_(True))
        )
        user = user_result.scalar_one_or_none()
        if user and user.feishu_open_id and user.feishu_open_id not in seen_open_ids:
            seen_open_ids.add(user.feishu_open_id)
            assignment = SuggestionAssignment(
                suggestion_id=suggestion.id,
                assignee_user_id=user.id,
                assignee_open_id=user.feishu_open_id,
                status="pending",
            )
            db.add(assignment)
            await db.flush()
            recipients.append({
                "assignee_open_id": user.feishu_open_id,
                "assignment_id": assignment.id,
            })

    if not recipients:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="所选部门未配置负责人且所选指派人无飞书 open_id,无法发送审批卡片",
        )

    await db.commit()

    # 4. 后台发送飞书卡片
    background_tasks.add_task(
        _send_cards_task,
        suggestion_id=suggestion.id,
        content=suggestion.content,
        highlights=suggestion.highlights,
        innovation_ideas=suggestion.innovation_ideas,
        dept_names=dept_names,
        assignments=recipients,
    )

    logger.info(
        f"匿名建议已提交: suggestion={suggestion.id}, recipients={len(recipients)}, query_code={query_code}",
        extra={"action": "suggestion.submit", "suggestion_id": suggestion.id, "recipients_count": len(recipients)},
    )

    return SuggestionSubmitResponse(
        query_code=query_code,
        message="提交成功，请保存查询码用于查询进度",
    )


@router.get("/track/{query_code}", response_model=SuggestionTrackResponse)
async def track_suggestion(
    query_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["suggestion:submit"])),
):
    """凭查询码查询建议进度（需登录，且查询码须属于当前用户）。"""
    result = await db.execute(
        select(Suggestion).where(Suggestion.query_code == query_code)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="查询码无效")

    # 校验该查询码是否属于当前用户
    if suggestion.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查询此建议")

    return SuggestionTrackResponse(
        status=suggestion.status,
        status_text=status_text(suggestion.status),
        created_at=suggestion.created_at,
        archived_at=suggestion.archived_at,
        market_result=suggestion.market_result,
        reject_reason=suggestion.reject_reason,
    )


@router.get("/my-codes/list")
async def list_my_suggestion_codes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["suggestion:submit"])),
):
    """获取当前用户提交的所有建议查询码列表（用于查询页下拉选择）。"""
    result = await db.execute(
        select(
            Suggestion.id,
            Suggestion.query_code,
            Suggestion.status,
            Suggestion.created_at,
            Suggestion.content,
        )
        .where(Suggestion.submitter_id == current_user.id)
        .order_by(Suggestion.created_at.desc())
    )
    rows = result.all()
    return {
        "items": [
            {
                "id": row.id,
                "queryCode": row.query_code,
                "status": row.status,
                "createdAt": row.created_at.isoformat() if row.created_at else None,
                "contentPreview": (row.content[:50] + "...") if row.content and len(row.content) > 50 else row.content,
            }
            for row in rows
        ]
    }


@router.get("", response_model=SuggestionListResponse)
async def list_suggestions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["suggestion:read"])),
):
    """建议列表（管理端）。"""
    query = select(Suggestion).options(selectinload(Suggestion.assignments))
    count_query = select(Suggestion)

    if status:
        query = query.where(Suggestion.status == status)
        count_query = count_query.where(Suggestion.status == status)

    # 总数
    from sqlalchemy import func

    total_result = await db.execute(select(func.count()).select_from(count_query.subquery()))
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(Suggestion.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    suggestions = result.scalars().all()

    return SuggestionListResponse(
        total=total,
        items=[_build_suggestion_response(s) for s in suggestions],
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size > 0 else 1,
    )


@router.get("/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["suggestion:read"])),
):
    """建议详情。"""
    result = await db.execute(
        select(Suggestion)
        .options(selectinload(Suggestion.assignments))
        .where(Suggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")

    # 预加载 assignment 关联
    for a in suggestion.assignments:
        _ = a.department
        _ = a.assignee_user

    return _build_suggestion_response(suggestion)


@router.put("/{suggestion_id}/archive", response_model=SuggestionResponse)
async def archive_suggestion(
    suggestion_id: int,
    data: SuggestionArchiveIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["suggestion:archive"])),
):
    """市场部存档（填写执行结果）。"""
    result = await db.execute(
        select(Suggestion)
        .options(selectinload(Suggestion.assignments))
        .where(Suggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")

    if suggestion.status != SuggestionStatus.APPROVED:
        raise HTTPException(status_code=400, detail="仅审批通过的建议可存档")

    # ND-6 修复（第二轮审查）：API 路径 market_result 无长度校验，与回调路径
    # _handle_suggestion_archive 的 2000 字符截断行为不一致。超长文本会导致
    # 飞书卡片渲染异常。统一截断到 2000 字符（DB 列为 Text 无长度限制，但
    # 卡片渲染有上限）。
    market_result_raw = data.market_result or ""
    if len(market_result_raw) > 2000:
        logger.info(
            f"market_result 截断: original_len={len(market_result_raw)}, truncated_to=2000",
            extra={
                "action": "suggestion.archive",
                "suggestion_id": suggestion_id,
                "original_len": len(market_result_raw),
                "truncated_to": 2000,
            },
        )
        market_result_raw = market_result_raw[:2000]

    suggestion.status = SuggestionStatus.ARCHIVED
    suggestion.market_result = market_result_raw
    suggestion.market_reviewer_id = current_user.id
    suggestion.archived_at = now_shanghai()
    await db.commit()
    await db.refresh(suggestion)

    logger.info(
        f"建议已存档: suggestion={suggestion_id}, reviewer={current_user.username}",
        extra={"action": "suggestion.archive", "suggestion_id": suggestion_id, "reviewer": current_user.username},
    )

    # 预加载 assignment 关联
    for a in suggestion.assignments:
        _ = a.department
        _ = a.assignee_user

    return _build_suggestion_response(suggestion)
