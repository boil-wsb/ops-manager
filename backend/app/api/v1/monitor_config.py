"""
Prometheus 监控主机配置管理 API 路由。

管理 git-repos/prometheus/conf/prometheus/ 下的服务器监控配置文件
（linux_server.json / windows_server.json），前端结构化表单增删改主机，
一键提交（写盘 + git commit + push）到 GitLab。
鉴权：读 monitor:read，增 monitor:create，改/提交 monitor:update，删 monitor:delete。
"""

import asyncio

from fastapi import APIRouter, Depends, Request

from app.api.deps import require_permissions
from app.core.audit import audit_log
from app.core.responses import api_error, api_response
from app.services.monitor_config import MonitorConfigService
from app.services.monitor_config.monitor_config_service import get_monitor_config_service

router = APIRouter(prefix="/monitor-config")


@router.get("/hosts")
async def list_hosts(
    _: None = Depends(require_permissions(["monitor:read"])),
    svc: MonitorConfigService = Depends(get_monitor_config_service),
):
    """合并返回 linux+windows 主机列表。"""
    try:
        result = await asyncio.to_thread(svc.read_hosts)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.get("/pending")
async def pending_changes(
    _: None = Depends(require_permissions(["monitor:read"])),
    svc: MonitorConfigService = Depends(get_monitor_config_service),
):
    """返回当前暂存（未提交）的操作摘要，供前端刷新/多标签页恢复提交按钮状态。"""
    try:
        result = await asyncio.to_thread(svc.pending_summary)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/hosts")
@audit_log(operation_type="CREATE", module="monitor_config", object_type="Host")
async def add_host(
    request: Request,
    body: dict,
    _: None = Depends(require_permissions(["monitor:create"])),
    svc: MonitorConfigService = Depends(get_monitor_config_service),
):
    """新增主机（body: file, ip, port, env, job, instance）暂存，commit 时统一写盘。"""
    try:
        result = await asyncio.to_thread(svc.add_host, body)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.put("/hosts")
@audit_log(operation_type="UPDATE", module="monitor_config", object_type="Host")
async def update_host(
    request: Request,
    body: dict,
    _: None = Depends(require_permissions(["monitor:update"])),
    svc: MonitorConfigService = Depends(get_monitor_config_service),
):
    """更新主机（body: file, index, ...）。"""
    try:
        result = await asyncio.to_thread(svc.update_host, body)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.delete("/hosts")
@audit_log(operation_type="DELETE", module="monitor_config", object_type="Host")
async def delete_host(
    request: Request,
    body: dict,
    _: None = Depends(require_permissions(["monitor:delete"])),
    svc: MonitorConfigService = Depends(get_monitor_config_service),
):
    """删除主机（body: file, index）。"""
    try:
        result = await asyncio.to_thread(svc.delete_host, body)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/commit")
@audit_log(operation_type="UPDATE", module="monitor_config", object_type="GitRepo")
async def commit_hosts(
    request: Request,
    body: dict,
    _: None = Depends(require_permissions(["monitor:update"])),
    svc: MonitorConfigService = Depends(get_monitor_config_service),
):
    """一键提交：写盘变更 + git commit + push（body: message 可选，由前端自动生成）。"""
    message = (body.get("message") or "").strip()
    try:
        result = await asyncio.to_thread(svc.commit, message)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)


@router.post("/push")
@audit_log(operation_type="UPDATE", module="monitor_config", object_type="GitRepo")
async def push_commits(
    request: Request,
    _: None = Depends(require_permissions(["monitor:update"])),
    svc: MonitorConfigService = Depends(get_monitor_config_service),
):
    """仅推送本地已存在的提交到远端（与前端按钮权限口径一致）。"""
    try:
        result = await asyncio.to_thread(svc.push_pending_commits)
    except Exception as e:
        return api_error(str(getattr(e, "detail", e)))
    return api_response(result)