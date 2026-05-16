from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig
from app.schemas.system_config import SystemConfigCreate, SystemConfigUpdate


class CRUDSystemConfig:
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        group: str | None = None,
        key: str | None = None,
    ) -> tuple[list[SystemConfig], int]:
        query = select(SystemConfig)
        count_query = select(func.count(SystemConfig.id))

        filters = []
        if group:
            filters.append(SystemConfig.group == group)
        if key:
            filters.append(SystemConfig.key.ilike(f"%{key}%"))

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        query = query.offset(skip).limit(limit).order_by(SystemConfig.id.asc())
        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_by_key(self, db: AsyncSession, key: str) -> SystemConfig | None:
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        return result.scalar_one_or_none()

    async def get_value(self, db: AsyncSession, key: str, default: str | None = None) -> str | None:
        config = await self.get_by_key(db, key)
        return config.value if config else default

    async def upsert_by_key(
        self,
        db: AsyncSession,
        *,
        key: str,
        value: str,
        group: str,
        description: str | None = None,
        is_secret: bool = False,
    ) -> SystemConfig:
        existing = await self.get_by_key(db, key)
        if existing:
            return existing

        db_obj = SystemConfig(
            key=key,
            value=value,
            group=group,
            description=description,
            is_secret=is_secret,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: SystemConfigCreate,
    ) -> SystemConfig:
        db_obj = SystemConfig(
            key=obj_in.key,
            value=obj_in.value,
            group=obj_in.group,
            description=obj_in.description,
            is_secret=obj_in.is_secret,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: SystemConfig,
        obj_in: SystemConfigUpdate,
    ) -> SystemConfig:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, key: str) -> bool:
        config = await self.get_by_key(db, key)
        if config:
            await db.delete(config)
            await db.commit()
            return True
        return False


crud_system_config = CRUDSystemConfig()
