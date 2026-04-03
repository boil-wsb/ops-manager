"""
Asset CRUD operations.
"""
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.asset import Asset, AssetHistory, AssetStatus, AssetType, Label
from app.schemas.asset import AssetCreate, AssetUpdate


class CRUDAsset(CRUDBase[Asset, AssetCreate, AssetUpdate]):
    """Asset CRUD operations."""

    async def get_by_asset_id(
        self,
        db: AsyncSession,
        *,
        asset_id: str
    ) -> Asset | None:
        """Get asset by asset_id."""
        result = await db.execute(
            select(Asset).where(Asset.asset_id == asset_id)
        )
        return result.scalar_one_or_none()

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        asset_type: str | None = None,
        status: str | None = None,
        idc: str | None = None,
        keyword: str | None = None,
        label_ids: list[int] | None = None,
        owner_id: int | None = None,
    ) -> tuple[list[Asset], int]:
        """Get assets with filters and pagination."""
        query = select(Asset)

        filters = []
        if asset_type:
            filters.append(Asset.asset_type == AssetType(asset_type))
        if status:
            filters.append(Asset.status == AssetStatus(status))
        if idc:
            filters.append(Asset.idc == idc)
        if keyword:
            filters.append(
                or_(
                    Asset.name.ilike(f"%{keyword}%"),
                    Asset.asset_id.ilike(f"%{keyword}%"),
                    Asset.ip_address.ilike(f"%{keyword}%")
                )
            )
        if owner_id is not None:
            filters.append(Asset.owner_id == owner_id)

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create_with_labels(
        self,
        db: AsyncSession,
        *,
        obj_in: AssetCreate,
        owner_id: int | None = None
    ) -> Asset:
        """Create asset with labels."""
        from app.models.user import User

        resolved_owner_id = owner_id

        if resolved_owner_id is None and obj_in.owner_id is not None:
            resolved_owner_id = obj_in.owner_id

        if resolved_owner_id is None and obj_in.owner_name:
            result = await db.execute(
                select(User.id).where(
                    User.full_name == obj_in.owner_name,
                    User.feishu_open_id != None,
                )
            )
            user_id = result.scalar_one_or_none()
            if user_id:
                resolved_owner_id = user_id

        db_obj = Asset(
            asset_id=obj_in.asset_id,
            name=obj_in.name,
            asset_type=AssetType(obj_in.asset_type),
            status=AssetStatus(obj_in.status),
            ip_address=obj_in.ip_address,
            private_ip=obj_in.private_ip,
            mac_address=obj_in.mac_address,
            cpu_cores=obj_in.cpu_cores,
            memory_gb=obj_in.memory_gb,
            disk_gb=obj_in.disk_gb,
            os_type=obj_in.os_type,
            os_version=obj_in.os_version,
            idc=obj_in.idc,
            region=obj_in.region,
            rack=obj_in.rack,
            description=obj_in.description,
            owner_id=resolved_owner_id,
            owner_name=obj_in.owner_name,
        )

        # Add labels if provided
        if obj_in.label_ids:
            labels_result = await db.execute(
                select(Label).where(Label.id.in_(obj_in.label_ids))
            )
            db_obj.labels = list(labels_result.scalars().all())

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # Create history record
        history = AssetHistory(
            asset_id=db_obj.id,
            action="create",
            changes={"data": obj_in.model_dump()},
            operator_id=owner_id
        )
        db.add(history)
        await db.commit()

        return db_obj

    async def update_with_labels(
        self,
        db: AsyncSession,
        *,
        db_obj: Asset,
        obj_in: AssetUpdate,
        operator_id: int | None = None
    ) -> Asset:
        """Update asset with labels."""
        changes = {}

        update_data = obj_in.model_dump(exclude_unset=True, exclude={"label_ids"})

        if "owner_name" in update_data and update_data["owner_name"] is not None:
            owner_name_value = update_data["owner_name"]
            owner_id_value = update_data.get("owner_id")

            if owner_id_value is None and owner_name_value:
                from app.models.user import User
                result = await db.execute(
                    select(User.id).where(
                        User.full_name == owner_name_value,
                        User.feishu_open_id != None,
                    )
                )
                resolved_owner_id = result.scalar_one_or_none()
                if resolved_owner_id:
                    update_data["owner_id"] = resolved_owner_id

        for field, value in update_data.items():
            if value is not None:
                old_value = getattr(db_obj, field)
                if old_value != value:
                    changes[field] = {"old": old_value, "new": value}
                    setattr(db_obj, field, value)

        # Update labels if provided
        if obj_in.label_ids is not None:
            labels_result = await db.execute(
                select(Label).where(Label.id.in_(obj_in.label_ids))
            )
            db_obj.labels = list(labels_result.scalars().all())
            changes["labels"] = {"new": obj_in.label_ids}

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # Create history record
        if changes:
            history = AssetHistory(
                asset_id=db_obj.id,
                action="update",
                changes=changes,
                operator_id=operator_id
            )
            db.add(history)
            await db.commit()

        return db_obj


class CRUDLabel(CRUDBase[Label, Any, Any]):
    """Label CRUD operations."""

    async def get_by_name(
        self,
        db: AsyncSession,
        *,
        name: str
    ) -> Label | None:
        """Get label by name."""
        result = await db.execute(
            select(Label).where(Label.name == name)
        )
        return result.scalar_one_or_none()


crud_asset = CRUDAsset(Asset)
crud_label = CRUDLabel(Label)
