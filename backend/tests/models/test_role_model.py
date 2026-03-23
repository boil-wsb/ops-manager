"""
Tests for Role model.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Role, Permission, role_permissions


@pytest.mark.asyncio
async def test_create_role(db_session: AsyncSession):
    """Test creating a role."""
    role = Role(name="Test Role", description="Test description")
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    assert role.id is not None
    assert role.name == "Test Role"
    assert role.description == "Test description"
    assert role.is_system is False
    assert role.is_active is True
    assert role.created_at is not None
    assert role.updated_at is not None


@pytest.mark.asyncio
async def test_create_role_with_defaults(db_session: AsyncSession):
    """Test creating a role with default values."""
    role = Role(name="Default Test Role")
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    assert role.is_system is False
    assert role.is_active is True
    assert role.description is None


@pytest.mark.asyncio
async def test_role_repr(db_session: AsyncSession):
    """Test role string representation."""
    role = Role(name="Repr Test Role")
    db_session.add(role)
    await db_session.commit()

    assert repr(role) == "<Role Repr Test Role>"


@pytest.mark.asyncio
async def test_add_permission_to_role(db_session: AsyncSession):
    """Test adding permissions to a role."""
    role = Role(name="Perm Test Role")
    db_session.add(role)
    await db_session.commit()

    permission = Permission(
        code="test:read",
        name="Test Read",
        module="test",
        action="read"
    )
    db_session.add(permission)
    await db_session.commit()

    role.permissions.append(permission)
    await db_session.commit()
    await db_session.refresh(role)

    assert len(role.permissions) == 1
    assert role.permissions[0].code == "test:read"
    assert role.permissions[0].name == "Test Read"


@pytest.mark.asyncio
async def test_role_permission_many_to_many(db_session: AsyncSession):
    """Test role-permission many-to-many relationship."""
    role = Role(name="M2M Test Role")
    db_session.add(role)
    await db_session.commit()

    permissions = [
        Permission(code="test:create", name="Create", module="test", action="create"),
        Permission(code="test:read", name="Read", module="test", action="read"),
        Permission(code="test:update", name="Update", module="test", action="update"),
    ]
    for p in permissions:
        db_session.add(p)
    await db_session.commit()

    role.permissions.extend(permissions)
    await db_session.commit()
    await db_session.refresh(role)

    assert len(role.permissions) == 3
    permission_codes = [p.code for p in role.permissions]
    assert "test:create" in permission_codes
    assert "test:read" in permission_codes
    assert "test:update" in permission_codes


@pytest.mark.asyncio
async def test_remove_permission_from_role(db_session: AsyncSession):
    """Test removing a permission from a role."""
    role = Role(name="Remove Perm Test Role")
    db_session.add(role)
    await db_session.commit()

    permission = Permission(
        code="test:delete",
        name="Delete",
        module="test",
        action="delete"
    )
    db_session.add(permission)
    await db_session.commit()

    role.permissions.append(permission)
    await db_session.commit()
    await db_session.refresh(role)

    assert len(role.permissions) == 1

    role.permissions.remove(permission)
    await db_session.commit()
    await db_session.refresh(role)

    assert len(role.permissions) == 0


@pytest.mark.asyncio
async def test_role_unique_name_constraint(db_session: AsyncSession):
    """Test that role name must be unique."""
    role1 = Role(name="Unique Test Role")
    db_session.add(role1)
    await db_session.commit()

    role2 = Role(name="Unique Test Role")
    db_session.add(role2)
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(select(Role).where(Role.name == "Unique Test Role"))
    roles = result.scalars().all()

    assert len(roles) == 1


@pytest.mark.asyncio
async def test_role_is_system_flag(db_session: AsyncSession):
    """Test role is_system flag."""
    system_role = Role(name="System Role", is_system=True)
    regular_role = Role(name="Regular Role", is_system=False)

    db_session.add(system_role)
    db_session.add(regular_role)
    await db_session.commit()
    await db_session.refresh(system_role)
    await db_session.refresh(regular_role)

    assert system_role.is_system is True
    assert regular_role.is_system is False


@pytest.mark.asyncio
async def test_role_is_active_flag(db_session: AsyncSession):
    """Test role is_active flag."""
    active_role = Role(name="Active Role", is_active=True)
    inactive_role = Role(name="Inactive Role", is_active=False)

    db_session.add(active_role)
    db_session.add(inactive_role)
    await db_session.commit()
    await db_session.refresh(active_role)
    await db_session.refresh(inactive_role)

    assert active_role.is_active is True
    assert inactive_role.is_active is False


@pytest.mark.asyncio
async def test_permission_back_populates(db_session: AsyncSession):
    """Test permission back_populates to roles."""
    role = Role(name="Back Populates Test Role")
    db_session.add(role)
    await db_session.commit()

    permission = Permission(
        code="test:back_populates",
        name="Back Populates Test",
        module="test",
        action="back_populates"
    )
    db_session.add(permission)
    await db_session.commit()

    role.permissions.append(permission)
    await db_session.commit()

    await db_session.refresh(permission)

    assert len(permission.roles) == 1
    assert permission.roles[0].name == "Back Populates Test Role"
