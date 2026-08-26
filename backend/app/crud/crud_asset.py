"""
Asset CRUD operations.
"""

from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.models.asset import Asset, AssetHistory, AssetStatus, AssetType, Label
from app.schemas.asset import AssetCreate, AssetUpdate

logger = get_logger(__name__)


async def _resolve_owner_id_by_name(db: AsyncSession, owner_name: str) -> tuple[int | None, bool]:
    """通过 owner_name 解析 owner_id。

    I-12 修复：使用 limit(2) 检测重名用户，重名时记 WARNING 日志并取 id 最大的一条。
    返回 (owner_id, has_duplicates)。
    """
    from app.models.user import User

    result = await db.execute(
        select(User.id)
        .where(
            User.full_name == owner_name,
            User.feishu_open_id.isnot(None),
        )
        .order_by(User.id.desc())
        .limit(2)
    )
    user_ids = list(result.scalars().all())
    if not user_ids:
        return None, False
    if len(user_ids) > 1:
        logger.warning(
            f"检测到重名用户，取 id 最大的一条: owner_name={owner_name}, matched_ids={user_ids}",
            extra={
                "action": "asset.resolve_owner",
                "owner_name": owner_name,
                "matched_ids": user_ids,
            },
        )
        return user_ids[0], True
    return user_ids[0], False


class CRUDAsset(CRUDBase[Asset, AssetCreate, AssetUpdate]):
    """Asset CRUD operations."""

    async def get_by_asset_id(self, db: AsyncSession, *, asset_id: str) -> Asset | None:
        """Get asset by asset_id."""
        result = await db.execute(select(Asset).where(Asset.asset_id == asset_id))
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
        exclude_retired: bool = True,
    ) -> tuple[list[Asset], int]:
        """Get assets with filters and pagination."""
        query = select(Asset).options(
            selectinload(Asset.labels),
            selectinload(Asset.owner),
        )

        filters = []
        if asset_type:
            filters.append(Asset.asset_type == AssetType(asset_type))
        if status:
            filters.append(Asset.status == AssetStatus(status))
        elif exclude_retired:
            # 默认排除已退役资产，除非用户主动筛选 RETIRED 状态或显式禁用排除
            filters.append(Asset.status != AssetStatus.RETIRED)
        if idc:
            filters.append(Asset.idc == idc)
        if keyword:
            filters.append(
                or_(
                    Asset.name.ilike(f"%{keyword}%"),
                    Asset.asset_id.ilike(f"%{keyword}%"),
                    Asset.ip_address.ilike(f"%{keyword}%"),
                )
            )
        if owner_id is not None:
            filters.append(Asset.owner_id == owner_id)

        if filters:
            query = query.where(and_(*filters))

        count_query = select(func.count(Asset.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply default IP address ordering and pagination
        query = query.order_by(Asset.ip_address).offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create_with_labels(
        self, db: AsyncSession, *, obj_in: AssetCreate, owner_id: int | None = None
    ) -> Asset:
        """Create asset with labels."""
        resolved_owner_id = owner_id

        if resolved_owner_id is None and obj_in.owner_id is not None:
            resolved_owner_id = obj_in.owner_id

        if resolved_owner_id is None and obj_in.owner_name:
            # I-12: 使用 _resolve_owner_id_by_name 检测重名用户
            # ND-5: 调用方检查 has_duplicates，重名时记 WARNING（不阻断，但暴露问题）
            resolved_owner_id, has_duplicates = await _resolve_owner_id_by_name(
                db, obj_in.owner_name
            )
            # ND-4: owner_name 解析失败时（用户名不存在），resolved_owner_id 为 None，
            # 不应保留 owner_name 与旧 owner_id 的不一致状态，同步清空 owner_name
            if resolved_owner_id is None:
                logger.warning(
                    f"owner_name 解析失败，用户不存在，已清空 owner_name: {obj_in.owner_name}",
                    extra={
                        "action": "asset.create",
                        "owner_name": obj_in.owner_name,
                        "resolved": False,
                    },
                )
                # 清空 owner_name，避免 owner_name 与 owner_id 不一致
                # 注意：这里修改 obj_in.owner_name，下面构造 db_obj 时会使用
                obj_in.owner_name = None

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
            labels_result = await db.execute(select(Label).where(Label.id.in_(obj_in.label_ids)))
            db_obj.labels = list(labels_result.scalars().all())

        db.add(db_obj)

        # NC-1 修复：必须先 flush 让 db_obj.id 生成（db.add 不会立即 INSERT），
        # 否则 AssetHistory.asset_id=db_obj.id 为 None，NOT NULL 约束违反导致 500。
        # I-14 合并为单次 commit 时遗漏了 flush，导致资产创建接口整体不可用。
        await db.flush()

        # I-14: 合并为单次 commit，资产和审计历史原子写入
        history = AssetHistory(
            asset_id=db_obj.id,
            action="create",
            changes={"data": obj_in.model_dump()},
            operator_id=owner_id,
        )
        db.add(history)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    async def update_with_labels(
        self,
        db: AsyncSession,
        *,
        db_obj: Asset,
        obj_in: AssetUpdate,
        operator_id: int | None = None,
    ) -> Asset:
        """Update asset with labels."""
        changes = {}

        update_data = obj_in.model_dump(exclude_unset=True, exclude={"label_ids"})

        if "owner_name" in update_data:
            owner_name_value = update_data["owner_name"]
            owner_id_value = update_data.get("owner_id")

            if owner_name_value is not None:
                # I-12: 使用 _resolve_owner_id_by_name 检测重名用户
                if owner_id_value is None and owner_name_value:
                    # ND-5: 调用方检查 has_duplicates，重名时记 WARNING（不阻断）
                    resolved_owner_id, has_duplicates = await _resolve_owner_id_by_name(
                        db, owner_name_value
                    )
                    if resolved_owner_id:
                        update_data["owner_id"] = resolved_owner_id
                    else:
                        # ND-4: owner_name 解析失败时（用户名不存在），
                        # 同步清空 owner_id，避免 owner_name 与 owner_id 不一致
                        logger.warning(
                            f"owner_name 解析失败，用户不存在，已同步清空 owner_id: {owner_name_value}",
                            extra={
                                "action": "asset.update",
                                "owner_name": owner_name_value,
                                "resolved": False,
                            },
                        )
                        update_data["owner_id"] = None
            else:
                # I-13: 显式设置 owner_name=None 表示清空负责人，同步清空 owner_id
                update_data["owner_id"] = None

        # I-13: 移除 `if value is not None` 守卫，允许显式 None 清空字段。
        # exclude_unset=True 已确保只有用户显式提供的字段才在 update_data 中，
        # 因此 None 值表示用户想清空该字段（如 description/mac_address/private_ip）。
        for field, value in update_data.items():
            old_value = getattr(db_obj, field)
            if old_value != value:
                changes[field] = {"old": old_value, "new": value}
                setattr(db_obj, field, value)

        # Update labels if provided
        if obj_in.label_ids is not None:
            labels_result = await db.execute(select(Label).where(Label.id.in_(obj_in.label_ids)))
            db_obj.labels = list(labels_result.scalars().all())
            changes["labels"] = {"new": obj_in.label_ids}

        db.add(db_obj)

        # I-14: 合并为单次 commit，资产变更和审计历史原子写入
        if changes:
            history = AssetHistory(
                asset_id=db_obj.id, action="update", changes=changes, operator_id=operator_id
            )
            db.add(history)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj


class CRUDLabel(CRUDBase[Label, Any, Any]):
    """Label CRUD operations."""

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Label | None:
        """Get label by name."""
        result = await db.execute(select(Label).where(Label.name == name))
        return result.scalar_one_or_none()


crud_asset = CRUDAsset(Asset)
crud_label = CRUDLabel(Label)
