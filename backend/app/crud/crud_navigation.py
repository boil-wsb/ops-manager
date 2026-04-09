"""
CRUD operations for navigation links.
"""

from collections import defaultdict

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.navigation import NavigationLink
from app.models.permission import Role
from app.schemas.navigation import NavigationLinkCreate, NavigationLinkUpdate


class CRUDNavigationLink(CRUDBase[NavigationLink, NavigationLinkCreate, NavigationLinkUpdate]):
    """CRUD operations for navigation links."""

    async def get_active_links_for_user(
        self, db: AsyncSession, user_role_ids: set[int], category: str | None = None
    ) -> list[NavigationLink]:
        """Get active navigation links visible to user based on their roles."""

        conditions = [NavigationLink.is_active]
        if category:
            conditions.append(NavigationLink.category == category)

        query = (
            select(NavigationLink)
            .options(selectinload(NavigationLink.roles))
            .where(and_(*conditions))
            .order_by(NavigationLink.sort_order, NavigationLink.id)
        )

        result = await db.execute(query)
        links = result.scalars().all()

        filtered_links = []
        for link in links:
            if not link.roles:
                filtered_links.append(link)
            else:
                link_role_ids = {role.id for role in link.roles}
                if user_role_ids & link_role_ids:
                    filtered_links.append(link)

        return filtered_links

    async def get_grouped_links_for_user(self, db: AsyncSession, user_role_ids: set[int]) -> dict:
        """Get navigation links grouped by category for a user."""
        links = await self.get_active_links_for_user(db, user_role_ids)
        grouped = defaultdict(list)
        for link in links:
            grouped[link.category].append(link)
        return dict(grouped)

    async def get_active_links(
        self, db: AsyncSession, category: str | None = None
    ) -> list[NavigationLink]:
        """Get all active navigation links, optionally filtered by category."""
        conditions = [NavigationLink.is_active]
        if category:
            conditions.append(NavigationLink.category == category)

        result = await db.execute(
            select(NavigationLink)
            .options(selectinload(NavigationLink.roles))
            .where(and_(*conditions))
            .order_by(NavigationLink.sort_order, NavigationLink.id)
        )
        return result.scalars().all()

    async def get_grouped_links(self, db: AsyncSession) -> dict:
        """Get navigation links grouped by category."""
        links = await self.get_active_links(db)
        grouped = defaultdict(list)
        for link in links:
            grouped[link.category].append(link)
        return dict(grouped)

    async def get_by_category(self, db: AsyncSession, category: str) -> list[NavigationLink]:
        """Get all links by category (including inactive)."""
        result = await db.execute(
            select(NavigationLink)
            .options(selectinload(NavigationLink.roles))
            .where(NavigationLink.category == category)
            .order_by(NavigationLink.sort_order, NavigationLink.id)
        )
        return result.scalars().all()

    async def get_multi_with_filter(
        self,
        db: AsyncSession,
        *,
        category: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[NavigationLink]:
        """Get multiple links with filters."""
        conditions = []
        if category is not None:
            conditions.append(NavigationLink.category == category)
        if is_active is not None:
            conditions.append(NavigationLink.is_active == is_active)

        query = select(NavigationLink).options(selectinload(NavigationLink.roles))
        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(
            query.order_by(NavigationLink.category, NavigationLink.sort_order)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count_with_filter(
        self, db: AsyncSession, *, category: str | None = None, is_active: bool | None = None
    ) -> int:
        """Count links with filters."""
        from sqlalchemy import func

        conditions = []
        if category is not None:
            conditions.append(NavigationLink.category == category)
        if is_active is not None:
            conditions.append(NavigationLink.is_active == is_active)

        query = select(func.count(NavigationLink.id))
        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_multi_with_access_filter(
        self,
        db: AsyncSession,
        *,
        category: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
        is_superadmin: bool = False,
        user_role_ids: list[int] | None = None,
    ) -> list[NavigationLink]:
        """Get multiple links with access control filters.

        For superadmin: returns all records.
        For non-superadmin: only returns records where roles is empty OR user has a matching role.
        """
        query = select(NavigationLink).options(selectinload(NavigationLink.roles))

        conditions = []
        if category is not None:
            conditions.append(NavigationLink.category == category)
        if is_active is not None:
            conditions.append(NavigationLink.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(
            query.order_by(NavigationLink.category, NavigationLink.sort_order)
            .offset(skip)
            .limit(limit)
        )
        all_links = result.scalars().all()

        if is_superadmin:
            return all_links

        filtered_links = []
        user_role_set = set(user_role_ids) if user_role_ids else set()
        for link in all_links:
            if not link.roles:
                filtered_links.append(link)
            else:
                link_role_ids = {role.id for role in link.roles}
                if user_role_set & link_role_ids:
                    filtered_links.append(link)

        return filtered_links

    async def count_with_access_filter(
        self,
        db: AsyncSession,
        *,
        category: str | None = None,
        is_active: bool | None = None,
        is_superadmin: bool = False,
        user_role_ids: list[int] | None = None,
    ) -> int:
        """Count links with access control filters.

        For superadmin: counts all records.
        For non-superadmin: only counts records where roles is empty OR user has a matching role.
        """

        query = select(NavigationLink).options(selectinload(NavigationLink.roles))

        conditions = []
        if category is not None:
            conditions.append(NavigationLink.category == category)
        if is_active is not None:
            conditions.append(NavigationLink.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(query)
        all_links = result.scalars().all()

        if is_superadmin:
            return len(all_links)

        user_role_set = set(user_role_ids) if user_role_ids else set()
        count = 0
        for link in all_links:
            if not link.roles:
                count += 1
            else:
                link_role_ids = {role.id for role in link.roles}
                if user_role_set & link_role_ids:
                    count += 1

        return count

    async def get_with_roles(self, db: AsyncSession, *, id: int) -> NavigationLink | None:
        """Get a navigation link by ID with roles loaded."""
        result = await db.execute(
            select(NavigationLink)
            .options(selectinload(NavigationLink.roles))
            .where(NavigationLink.id == id)
        )
        return result.scalar_one_or_none()

    async def create_with_roles(
        self, db: AsyncSession, *, obj_in: NavigationLinkCreate, role_ids: list[int] | None = None
    ) -> NavigationLink:
        """Create a navigation link with roles."""
        obj_data = obj_in.model_dump(exclude={"restrict_to_current_role"})
        db_obj = NavigationLink(**obj_data)

        if role_ids:
            roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
            db_obj.roles = list(roles_result.scalars().all())

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_with_roles(
        self,
        db: AsyncSession,
        *,
        db_obj: NavigationLink,
        obj_in: NavigationLinkUpdate,
        role_ids: list[int] | None = None,
    ) -> NavigationLink:
        """Update a navigation link with roles."""
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"restrict_to_current_role"})

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        if role_ids is not None:
            if role_ids:
                roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
                db_obj.roles = list(roles_result.scalars().all())
            else:
                db_obj.roles = []

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


navigation_link = CRUDNavigationLink(NavigationLink)
