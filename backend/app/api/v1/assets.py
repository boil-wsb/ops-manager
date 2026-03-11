"""
Asset management API routes.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_permissions
from app.crud.crud_asset import crud_asset, crud_label
from app.schemas.asset import (
    AssetCreate, AssetUpdate, AssetResponse, AssetListResponse,
    LabelCreate, LabelResponse, AssetFilter, AssetTreeNode
)
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


@router.get("/assets", response_model=AssetListResponse)
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
    return {"total": total, "items": items}


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
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
async def update_asset(
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


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
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
async def create_label(
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
async def delete_label(
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
