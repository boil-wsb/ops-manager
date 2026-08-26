"""
Git 仓库管理 API 路由。

在容器内对 GitLab 上的 prometheus 项目（http://192.168.23.19/devops/infrastructure/prometheus.git）
做读写双向管理：克隆、拉取、提交、推送、分支/标签切换、稀疏检出路径管理等。
鉴权：读操作 ops:read，写操作 ops:write。
"""

import asyncio

from fastapi import APIRouter, Depends, Request

from app.api.deps import require_permissions
from app.core.audit import audit_log
from app.core.responses import api_error, api_response
from app.services.git_repo import GitRepoService
from app.services.git_repo.git_repo_service import get_git_repo_service

router = APIRouter(prefix="/git-repos")


@router.get("/status")
async def get_status(
    _: None = Depends(require_permissions(["ops:read"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """仓库状态：是否已克隆、当前分支、HEAD、未提交改动。"""
    result = await asyncio.to_thread(svc.get_status)
    return api_response(result)


@router.get("/sync")
async def get_sync_status(
    _: None = Depends(require_permissions(["ops:read"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """本地与远端同步状态（ahead/behind/local_newer/remote_newer）。"""
    try:
        result = await asyncio.to_thread(svc.get_sync_status)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/clone")
@audit_log(operation_type="CREATE", module="git_repo", object_type="GitRepo")
async def clone(
    request: Request,
    _: None = Depends(require_permissions(["ops:write"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """克隆仓库并初始化 sparse-checkout（未克隆时）。"""
    try:
        result = await asyncio.to_thread(svc.ensure_clone)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.get("/sparse")
async def get_sparse(
    _: None = Depends(require_permissions(["ops:read"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """查看当前稀疏检出路径。"""
    try:
        result = await asyncio.to_thread(svc.get_sparse)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/sparse")
@audit_log(operation_type="UPDATE", module="git_repo", object_type="GitRepo")
async def set_sparse(
    request: Request,
    body: dict,
    _: None = Depends(require_permissions(["ops:write"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """更新稀疏检出路径。"""
    paths = body.get("paths", [])
    if not isinstance(paths, list) or not paths:
        return api_error("paths 必须为非空列表")
    try:
        result = await asyncio.to_thread(svc.set_sparse, paths)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/pull")
@audit_log(operation_type="UPDATE", module="git_repo", object_type="GitRepo")
async def pull(
    request: Request,
    _: None = Depends(require_permissions(["ops:write"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """拉取远端最新。"""
    try:
        result = await asyncio.to_thread(svc.pull)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/commit")
@audit_log(operation_type="CREATE", module="git_repo", object_type="GitRepo")
async def commit(
    request: Request,
    body: dict,
    _: None = Depends(require_permissions(["ops:write"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """提交本地改动（body: message, paths 可选）。"""
    message = body.get("message", "")
    paths = body.get("paths")
    if not message:
        return api_error("message 不能为空")
    try:
        result = await asyncio.to_thread(svc.commit, message, paths)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/push")
@audit_log(operation_type="UPDATE", module="git_repo", object_type="GitRepo")
async def push(
    request: Request,
    _: None = Depends(require_permissions(["ops:write"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """推送到远端当前分支。"""
    try:
        result = await asyncio.to_thread(svc.push)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.get("/branches")
async def list_branches(
    _: None = Depends(require_permissions(["ops:read"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """列分支与标签。"""
    try:
        result = await asyncio.to_thread(svc.list_branches)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/checkout")
@audit_log(operation_type="UPDATE", module="git_repo", object_type="GitRepo")
async def checkout(
    request: Request,
    body: dict,
    _: None = Depends(require_permissions(["ops:write"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """切换分支/标签/commit。"""
    ref = body.get("ref", "")
    if not ref:
        return api_error("ref 不能为空")
    try:
        result = await asyncio.to_thread(svc.checkout, ref)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.get("/log")
async def get_log(
    limit: int = 20,
    _: None = Depends(require_permissions(["ops:read"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """查看提交历史。"""
    size = max(1, min(limit, 100))
    try:
        result = await asyncio.to_thread(svc.get_log, size)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.get("/remote")
async def get_remote(
    _: None = Depends(require_permissions(["ops:read"])),
    svc: GitRepoService = Depends(get_git_repo_service),
):
    """远端地址（脱敏）。"""
    return api_response(svc.get_remote())
