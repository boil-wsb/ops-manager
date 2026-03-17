"""
Prometheus 代理 API
用于从前端访问 Prometheus 数据
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.response import api_response
from app.core.audit.decorator import audit_log
from app.models.user import User
from app.services.prometheus import get_prometheus_client, PrometheusClient
from app.crud.crud_asset import crud_asset
from app.schemas.asset import AssetCreate

router = APIRouter()


@router.get("/assets")
async def get_prometheus_assets(
    job: Optional[str] = Query(None, description="按 job 筛选"),
    env: Optional[str] = Query(None, description="按环境筛选"),
    status: Optional[str] = Query(None, description="按状态筛选 (up/down)"),
    client: PrometheusClient = Depends(get_prometheus_client),
    current_user: User = Depends(require_permissions(["asset:read"])),
):
    """
    获取 Prometheus 中的资产列表
    
    Args:
        job: 按 Prometheus job 名称筛选
        env: 按环境标签筛选
        status: 按在线状态筛选
    
    Returns:
        资产列表，包含节点信息和实时指标
    """
    nodes = await client.get_all_nodes_with_metrics()
    
    # 应用筛选条件
    filtered_nodes = nodes
    if job:
        filtered_nodes = [n for n in filtered_nodes if job in n.get("job", "")]
    if env:
        filtered_nodes = [n for n in filtered_nodes if n.get("env") == env]
    if status:
        filtered_nodes = [n for n in filtered_nodes if n.get("status") == status]
    
    # 添加资产类型映射
    for node in filtered_nodes:
        node["asset_type"] = client.map_job_to_asset_type(node.get("job", ""))
    
    return api_response(data={
        "items": filtered_nodes,
        "total": len(filtered_nodes)
    })


@router.get("/assets/{instance}")
async def get_prometheus_asset_detail(
    instance: str,
    client: PrometheusClient = Depends(get_prometheus_client),
    current_user: User = Depends(require_permissions(["asset:read"])),
):
    """
    获取 Prometheus 中指定资产的详细信息
    
    Args:
        instance: 资产实例地址 (IP 或主机名)
    
    Returns:
        资产详细信息和实时指标
    """
    # 获取所有节点并找到匹配的
    nodes = await client.get_all_nodes()
    node = None
    for n in nodes:
        if instance in n.get("instance", ""):
            node = n
            break
    
    if not node:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 获取状态和指标
    status = await client.get_node_status(instance)
    metrics = await client.get_node_metrics(instance)
    
    node["status"] = status
    node["metrics"] = metrics
    node["asset_type"] = client.map_job_to_asset_type(node.get("job", ""))
    
    return api_response(data=node)


@router.get("/metrics/{instance}")
async def get_prometheus_metrics(
    instance: str,
    client: PrometheusClient = Depends(get_prometheus_client),
    current_user: User = Depends(require_permissions(["asset:read"])),
):
    """
    获取指定资产的实时指标
    
    Args:
        instance: 资产实例地址
    
    Returns:
        CPU、内存、磁盘、网络等指标
    """
    metrics = await client.get_node_metrics(instance)
    return api_response(data=metrics)


@router.get("/query")
async def query_prometheus(
    query: str = Query(..., description="PromQL 查询语句"),
    client: PrometheusClient = Depends(get_prometheus_client),
    current_user: User = Depends(require_permissions(["asset:read"])),
):
    """
    执行通用 Prometheus 查询
    
    Args:
        query: PromQL 查询语句
    
    Returns:
        查询结果
    """
    result = await client.query(query)
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=500,
            detail=f"Prometheus 查询失败: {result.get('error')}"
        )
    
    return api_response(data=result.get("data", {}))


@router.post("/import")
@audit_log(operation_type="CREATE", module="asset", object_type="Asset")
async def import_from_prometheus(
    request: Request,
    import_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    client: PrometheusClient = Depends(get_prometheus_client),
    current_user: User = Depends(require_permissions(["asset:write"])),
):
    """
    从 Prometheus 导入资产到系统
    
    Request Body:
        - instance: Prometheus 实例地址 (必填)
        - owner_id: 负责人ID (可选)
        - description: 描述 (可选)
        - labels: 标签列表 (可选)
    
    Returns:
        创建的资产信息
    """
    instance = import_data.get("instance")
    if not instance:
        raise HTTPException(status_code=400, detail="instance 不能为空")
    
    # 获取 Prometheus 节点信息
    nodes = await client.get_all_nodes()
    node = None
    for n in nodes:
        if instance in n.get("instance", ""):
            node = n
            break
    
    if not node:
        raise HTTPException(status_code=404, detail="Prometheus 中不存在该资产")
    
    # 检查是否已存在
    existing = await crud_asset.get_by_ip(db, ip_address=instance)
    if existing:
        raise HTTPException(status_code=400, detail="该资产已存在")
    
    # 构建资产创建数据
    asset_data = AssetCreate(
        asset_id=f"AST-{instance.replace('.', '-')}"",
        name=node.get("nodename") or instance,
        asset_type=client.map_job_to_asset_type(node.get("job", "")),
        ip_address=instance,
        os_type=node.get("sysname", ""),
        os_version=node.get("release", ""),
        status="active" if node.get("job", "").startswith("windows") else "active",
        owner_id=import_data.get("owner_id"),
        description=import_data.get("description", f"从 Prometheus 导入: {node.get('job', '')}"),
    )
    
    # 创建资产
    asset = await crud_asset.create(db, obj_in=asset_data)
    
    # 如果有标签，添加标签
    labels = import_data.get("labels", [])
    if labels:
        # TODO: 添加标签关联逻辑
        pass
    
    return api_response(
        data={
            "id": asset.id,
            "asset_id": asset.asset_id,
            "name": asset.name,
            "ip_address": asset.ip_address,
        },
        message="资产导入成功"
    )


@router.get("/jobs")
async def get_prometheus_jobs(
    client: PrometheusClient = Depends(get_prometheus_client),
    current_user: User = Depends(require_permissions(["asset:read"])),
):
    """
    获取 Prometheus 中所有的 job 列表
    
    Returns:
        job 名称列表
    """
    result = await client.query("count by (job) (up)")
    
    jobs = []
    if result.get("status") == "success":
        for item in result.get("data", {}).get("result", []):
            job = item.get("metric", {}).get("job")
            if job:
                jobs.append(job)
    
    return api_response(data=jobs)


@router.get("/envs")
async def get_prometheus_envs(
    client: PrometheusClient = Depends(get_prometheus_client),
    current_user: User = Depends(require_permissions(["asset:read"])),
):
    """
    获取 Prometheus 中所有的环境标签列表
    
    Returns:
        环境标签列表
    """
    result = await client.query("count by (env) (up)")
    
    envs = []
    if result.get("status") == "success":
        for item in result.get("data", {}).get("result", []):
            env = item.get("metric", {}).get("env")
            if env:
                envs.append(env)
    
    return api_response(data=envs)
