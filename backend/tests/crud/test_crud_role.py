"""
Tests for CRUDRole.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_role import crud_role
from app.schemas.permission import RoleCreate, RoleUpdate


@pytest.mark.asyncio
async def test_create_role(db_session: AsyncSession):
    """Test creating a role."""
    role_in = RoleCreate(name="Test Role", description="Test description")
    role = await crud_role.create(db_session, obj_in=role_in)

    assert role.id is not None
    assert role.name == "Test Role"
    assert role.description == "Test description"
    assert role.is_system is False
    assert role.is_active is True


@pytest.mark.asyncio
async def test_get_role(db_session: AsyncSession):
    """Test getting a role by ID."""
    role_in = RoleCreate(name="Get Test Role", description="Test")
    created_role = await crud_role.create(db_session, obj_in=role_in)

    retrieved_role = await crud_role.get(db_session, id=created_role.id)

    assert retrieved_role is not None
    assert retrieved_role.id == created_role.id
    assert retrieved_role.name == "Get Test Role"


@pytest.mark.asyncio
async def test_get_role_not_found(db_session: AsyncSession):
    """Test getting a non-existent role."""
    role = await crud_role.get(db_session, id=99999)
    assert role is None


@pytest.mark.asyncio
async def test_get_multi_roles(db_session: AsyncSession):
    """Test getting multiple roles with pagination."""
    for i in range(5):
        role_in = RoleCreate(name=f"Multi Test Role {i}", description=f"Description {i}")
        await crud_role.create(db_session, obj_in=role_in)

    roles, total = await crud_role.get_multi(db_session, skip=0, limit=3)

    assert len(roles) == 3
    assert total >= 5


@pytest.mark.asyncio
async def test_get_multi_with_skip(db_session: AsyncSession):
    """Test get_multi with skip parameter."""
    for i in range(3):
        role_in = RoleCreate(name=f"Skip Test Role {i}", description=f"Desc {i}")
        await crud_role.create(db_session, obj_in=role_in)

    roles, total = await crud_role.get_multi(db_session, skip=2, limit=10)

    assert len(roles) >= 1
    assert total >= 3


@pytest.mark.asyncio
async def test_update_role(db_session: AsyncSession):
    """Test updating a role."""
    role_in = RoleCreate(name="Original Name", description="Original description")
    role = await crud_role.create(db_session, obj_in=role_in)

    update_data = RoleUpdate(name="Updated Name", description="Updated description")
    updated_role = await crud_role.update(db_session, db_obj=role, obj_in=update_data)

    assert updated_role.name == "Updated Name"
    assert updated_role.description == "Updated description"
    assert updated_role.id == role.id


@pytest.mark.asyncio
async def test_update_role_partial(db_session: AsyncSession):
    """Test partial update of a role."""
    role_in = RoleCreate(name="Partial Test", description="Original desc")
    role = await crud_role.create(db_session, obj_in=role_in)

    update_data = RoleUpdate(description="Only description updated")
    updated_role = await crud_role.update(db_session, db_obj=role, obj_in=update_data)

    assert updated_role.name == "Partial Test"
    assert updated_role.description == "Only description updated"


@pytest.mark.asyncio
async def test_update_role_is_active(db_session: AsyncSession):
    """Test updating role is_active field."""
    role_in = RoleCreate(name="Active Test", description="Test")
    role = await crud_role.create(db_session, obj_in=role_in)
    assert role.is_active is True

    update_data = RoleUpdate(is_active=False)
    updated_role = await crud_role.update(db_session, db_obj=role, obj_in=update_data)

    assert updated_role.is_active is False
