"""
Asset management API routes.
"""
from datetime import datetime
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_permissions
from app.crud.crud_asset import crud_asset, crud_label
from app.schemas.asset import (
    AssetCreate, AssetUpdate, AssetResponse, AssetListResponse,
    LabelCreate, LabelResponse, AssetFilter, AssetTreeNode
)
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import audit_log

router = APIRouter()


def api_response(data: Any = None, message: str = "操作成功") -> dict:
    """统一 API 响应格式"""
    return {"data": data, "message": message, "success": True}


@router.get("/assets")
async def list_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    asset_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    idc: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:read"])
):
    """List all assets with filters and pagination."""
    items, total = await crud_asset.get_multi_with_filters(
        db,
        skip=skip,
        limit=limit,
        asset_type=asset_type,
        status=status,
        idc=idc,
        keyword=keyword
    )
    # 使用 AssetResponse 序列化，确保字段别名生效
    serialized_items = [AssetResponse.model_validate(item).model_dump(by_alias=True) for item in items]
    return api_response(data={"total": total, "items": serialized_items})


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="asset", object_type="Asset")
async def create_asset(
    request: Request,
    obj_in: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:write"])
):
    """Create a new asset."""
    # Check if asset_id already exists
    existing = await crud_asset.get_by_asset_id(db, asset_id=obj_in.asset_id)
    if existing:
        raise ConflictError(detail=f"Asset with ID {obj_in.asset_id} already exists")
    
    asset = await crud_asset.create_with_labels(
        db,
        obj_in=obj_in,
        owner_id=current_user.id
    )
    return asset


# Prometheus sync routes - MUST be defined before /assets/{asset_id}
@router.post("/assets/sync")
@audit_log(operation_type="SYNC", module="asset", object_type="Asset")
async def trigger_asset_sync(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:admin"])
):
    """
    手动触发从 Prometheus 同步资产

    需要 asset:admin 权限
    """
    try:
        from app.tasks.asset_sync_tasks import sync_assets_from_prometheus_task

        task = sync_assets_from_prometheus_task.delay()

        return {
            "message": "Asset sync task triggered successfully",
            "task_id": task.id,
            "status": "pending"
        }
    except Exception as e:
        from app.services.prometheus.asset_sync import sync_assets_from_prometheus
        result = await sync_assets_from_prometheus(db)
        return {
            "message": "Asset sync completed",
            "result": result,
            "status": "completed"
        }


@router.post("/assets/sync-terminals")
@audit_log(operation_type="SYNC_TERMINALS", module="asset", object_type="Terminal")
async def sync_terminals_from_pc_info(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:admin"])
):
    """
    从 Prometheus pc_info 指标同步终端资产

    需要 asset:admin 权限
    """
    from app.services.prometheus.client import get_prometheus_client
    from app.models.asset import Asset, AssetType, AssetStatus, AssetSource, SyncStatus
    from sqlalchemy import select
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        prometheus_client = get_prometheus_client()
        terminals = await prometheus_client.get_all_terminals_with_metrics()
        
        synced_count = 0
        created_count = 0
        updated_count = 0
        errors = []
        
        for terminal in terminals:
            hostname = terminal.get("hostname", "")
            if not hostname:
                continue
            
            try:
                asset_id = f"TERMINAL-{hostname}"
                
                existing_result = await db.execute(
                    select(Asset).where(Asset.asset_id == asset_id)
                )
                existing_asset = existing_result.scalar_one_or_none()
                
                terminal_data = {
                    "asset_id": asset_id,
                    "name": hostname,
                    "asset_type": AssetType.TERMINAL,
                    "hostname": hostname,
                    "serial_number": terminal.get("serial_number"),
                    "uuid": terminal.get("uuid"),
                    "customer": terminal.get("customer"),
                    "source": AssetSource.PROMETHEUS.value,
                    "sync_status": SyncStatus.SYNCED.value,
                    "last_sync_time": datetime.utcnow(),
                    "status": AssetStatus.ACTIVE,
                    "labels_data": terminal.get("pc_info_labels", {}),
                }
                
                if terminal.get("cpu_cores"):
                    terminal_data["cpu_cores"] = int(terminal.get("cpu_cores"))
                if terminal.get("memory_total"):
                    terminal_data["memory_gb"] = int(terminal.get("memory_total") / (1024 * 1024 * 1024))
                if terminal.get("disk_total"):
                    terminal_data["disk_gb"] = int(terminal.get("disk_total") / (1024 * 1024 * 1024))
                if terminal.get("os_type"):
                    terminal_data["os_type"] = terminal.get("os_type")
                if terminal.get("os_version"):
                    terminal_data["os_version"] = terminal.get("os_version")
                if terminal.get("arch"):
                    terminal_data["arch"] = terminal.get("arch")
                
                if existing_asset:
                    for key, value in terminal_data.items():
                        if key != "asset_id":
                            setattr(existing_asset, key, value)
                    updated_count += 1
                else:
                    new_asset = Asset(**terminal_data)
                    db.add(new_asset)
                    created_count += 1
                
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Failed to sync terminal {hostname}: {e}")
                errors.append({"hostname": hostname, "error": str(e)})
        
        await db.commit()
        
        return {
            "message": "Terminal sync completed",
            "total_discovered": len(terminals),
            "synced": synced_count,
            "created": created_count,
            "updated": updated_count,
            "errors": errors,
        }
        
    except Exception as e:
        logger.error(f"Terminal sync failed: {e}")
        raise ConflictError(detail=f"Terminal sync failed: {str(e)}")


@router.get("/assets/terminals")
async def list_terminals(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:read"])
):
    """List terminal assets with filters and pagination."""
    items, total = await crud_asset.get_multi_with_filters(
        db,
        skip=skip,
        limit=limit,
        asset_type="TERMINAL",
        status=status,
        keyword=keyword
    )
    serialized_items = [AssetResponse.model_validate(item).model_dump(by_alias=True) for item in items]
    return api_response(data={"total": total, "items": serialized_items})


@router.get("/assets/discovery")
async def discover_prometheus_assets(
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:read"])
):
    """
    发现 Prometheus 中未导入的节点

    返回 Prometheus 中监控但尚未导入资产系统的节点列表
    """
    from app.services.prometheus.client import get_prometheus_client
    from app.crud.crud_asset import crud_asset

    # 获取 Prometheus 中的所有节点
    prometheus_client = get_prometheus_client()
    nodes = await prometheus_client.get_all_nodes()

    # 获取已存在的资产 IP 列表
    existing_assets, _ = await crud_asset.get_multi_with_filters(db, skip=0, limit=10000)
    existing_ips = {asset.ip_address for asset in existing_assets if asset.ip_address}

    # 筛选未导入的节点
    discovered_nodes = []
    for node in nodes:
        instance = node.get("instance", "")
        ip_address = instance.split(":")[0] if ":" in instance else instance

        if ip_address and ip_address not in existing_ips:
            discovered_nodes.append({
                "instance": instance,
                "ip_address": ip_address,
                "nodename": node.get("nodename", ""),
                "sysname": node.get("sysname", ""),
                "release": node.get("release", ""),
                "machine": node.get("machine", ""),
                "job": node.get("job", ""),
                "env": node.get("env", ""),
            })

    return {
        "total": len(nodes),
        "discovered": len(discovered_nodes),
        "existing": len(existing_ips),
        "nodes": discovered_nodes
    }


@router.post("/assets/discovery/{instance}/import")
@audit_log(operation_type="IMPORT", module="asset", object_type="Asset")
async def import_prometheus_asset(
    request: Request,
    instance: str,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:write"])
):
    """
    从 Prometheus 导入指定节点为资产（使用优化版本）

    Args:
        instance: Prometheus 实例标识 (URL 编码后的 IP:Port)
    """
    from urllib.parse import unquote
    from app.services.prometheus.asset_sync_optimized import OptimizedAssetSyncService
    import logging

    logger = logging.getLogger(__name__)

    try:
        # URL 解码 instance 参数
        decoded_instance = unquote(instance)
        logger.info(f"Importing asset from Prometheus: {decoded_instance}")

        # 创建优化的同步服务并导入
        service = OptimizedAssetSyncService(db)
        result = await service.sync_single_asset(decoded_instance)

        if result["success"]:
            asset_obj = result.get('asset')
            asset_id = asset_obj.asset_id if asset_obj else 'unknown'
            logger.info(f"Successfully imported asset: {asset_id}")
            return {
                "message": f"Asset imported successfully from {decoded_instance}",
                "action": result.get("action"),
                "asset": {
                    "id": asset_obj.id,
                    "asset_id": asset_obj.asset_id,
                    "name": asset_obj.name,
                    "ip_address": asset_obj.ip_address,
                } if asset_obj else None
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Failed to import asset {decoded_instance}: {error_msg}")
            raise ConflictError(detail=f"Failed to import asset: {error_msg}")
    except Exception as e:
        logger.exception(f"Exception during asset import: {e}")
        raise ConflictError(detail=f"Failed to import asset: {str(e)}")


@router.get("/assets/tree", response_model=List[AssetTreeNode])
async def get_asset_tree(
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:read"])
):
    """Get asset tree structure organized by IDC/Region/Rack."""
    # Get all assets
    assets, _ = await crud_asset.get_multi_with_filters(db, skip=0, limit=1000)
    
    # Build tree structure
    tree: dict = {}
    
    for asset in assets:
        idc = asset.idc or "Unknown IDC"
        region = asset.region or "Unknown Region"
        rack = asset.rack or "Unknown Rack"
        
        # Create IDC node
        if idc not in tree:
            tree[idc] = {"key": f"idc-{idc}", "title": idc, "children": {}}
        
        # Create Region node
        if region not in tree[idc]["children"]:
            tree[idc]["children"][region] = {
                "key": f"region-{idc}-{region}",
                "title": region,
                "children": {}
            }
        
        # Create Rack node
        if rack not in tree[idc]["children"][region]["children"]:
            tree[idc]["children"][region]["children"][rack] = {
                "key": f"rack-{idc}-{region}-{rack}",
                "title": rack,
                "children": []
            }
        
        # Add asset to rack
        tree[idc]["children"][region]["children"][rack]["children"].append({
            "key": f"asset-{asset.id}",
            "title": f"{asset.asset_id} - {asset.name}",
            "is_leaf": True,
            "data": {
                "id": asset.id,
                "asset_id": asset.asset_id,
                "name": asset.name,
                "type": asset.asset_type.value,
                "status": asset.status.value,
                "ip": asset.ip_address
            }
        })
    
    # Convert to list structure
    result = []
    for idc_node in tree.values():
        idc_children = []
        for region_node in idc_node["children"].values():
            region_children = []
            for rack_node in region_node["children"].values():
                rack_node["children"] = rack_node["children"]
                region_children.append(rack_node)
            region_node["children"] = region_children
            idc_children.append(region_node)
        idc_node["children"] = idc_children
        result.append(idc_node)
    
    return result


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:read"])
):
    """Get asset by ID."""
    asset = await crud_asset.get(db, id=asset_id)
    if not asset:
        raise NotFoundError(detail=f"Asset with ID {asset_id} not found")
    return asset


@router.put("/assets/{asset_id}", response_model=AssetResponse)
@audit_log(operation_type="UPDATE", module="asset", object_type="Asset")
async def update_asset(
    request: Request,
    asset_id: int,
    obj_in: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:write"])
):
    """Update asset."""
    asset = await crud_asset.get(db, id=asset_id)
    if not asset:
        raise NotFoundError(detail=f"Asset with ID {asset_id} not found")
    
    asset = await crud_asset.update_with_labels(
        db,
        db_obj=asset,
        obj_in=obj_in,
        operator_id=current_user.id
    )
    return asset


@router.post("/assets/batch-delete", status_code=status.HTTP_200_OK)
@audit_log(operation_type="BATCH_DELETE", module="asset", object_type="Asset")
async def batch_delete_assets(
    request: Request,
    asset_ids: List[int],
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:delete"])
):
    """Batch delete assets."""
    deleted_ids = []
    failed_ids = []

    for asset_id in asset_ids:
        asset = await crud_asset.get(db, id=asset_id)
        if asset:
            await crud_asset.delete(db, id=asset_id)
            deleted_ids.append(asset_id)
        else:
            failed_ids.append(asset_id)

    return {
        "deleted_count": len(deleted_ids),
        "failed_count": len(failed_ids),
        "deleted_ids": deleted_ids,
        "failed_ids": failed_ids,
    }


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="asset", object_type="Asset")
async def delete_asset(
    request: Request,
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:delete"])
):
    """Delete asset."""
    asset = await crud_asset.get(db, id=asset_id)
    if not asset:
        raise NotFoundError(detail=f"Asset with ID {asset_id} not found")

    await crud_asset.delete(db, id=asset_id)
    return None


@router.get("/assets/{asset_id}/metrics")
async def get_asset_metrics(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:read"])
):
    """
    获取资产的实时指标数据

    从 Prometheus 查询资产的 CPU、内存、磁盘等实时指标
    """
    from app.services.prometheus.client import get_prometheus_client

    # 获取资产信息
    asset = await crud_asset.get(db, id=asset_id)
    if not asset:
        raise NotFoundError(detail=f"Asset with ID {asset_id} not found")

    # 如果没有 IP 地址，无法查询指标
    if not asset.ip_address:
        return {
            "asset_id": asset_id,
            "asset_name": asset.name,
            "metrics": {},
            "error": "Asset has no IP address"
        }

    # 从 Prometheus 获取指标
    prometheus_client = get_prometheus_client()
    metrics = await prometheus_client.get_node_metrics(asset.ip_address)

    return {
        "asset_id": asset_id,
        "asset_name": asset.name,
        "ip_address": asset.ip_address,
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    }


# Label routes
@router.get("/labels", response_model=List[LabelResponse])
async def list_labels(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:read"])
):
    """List all labels."""
    labels = await crud_label.get_multi(db, skip=skip, limit=limit)
    return labels


@router.post("/labels", response_model=LabelResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="asset", object_type="Label")
async def create_label(
    request: Request,
    obj_in: LabelCreate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:write"])
):
    """Create a new label."""
    # Check if label name already exists
    existing = await crud_label.get_by_name(db, name=obj_in.name)
    if existing:
        raise ConflictError(detail=f"Label with name {obj_in.name} already exists")
    
    label = await crud_label.create(db, obj_in=obj_in)
    return label


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="asset", object_type="Label")
async def delete_label(
    request: Request,
    label_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["asset:delete"])
):
    """Delete label."""
    label = await crud_label.get(db, id=label_id)
    if not label:
        raise NotFoundError(detail=f"Label with ID {label_id} not found")

    await crud_label.delete(db, id=label_id)
    return None
