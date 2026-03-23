"""
Tests for CRUD permission operations.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_permission import crud_permission
from app.schemas.permission import PermissionCreate


@pytest.mark.asyncio
async def test_create_permission(db_session: AsyncSession):
    """Test create permission."""
    permission_in = PermissionCreate(
        code="test:create",
        name="Test Create",
        module="test",
        action="create",
        description="Test permission description",
        is_active=True
    )
    permission = await crud_permission.create(db_session, obj_in=permission_in)

    assert permission.id is not None
    assert permission.code == "test:create"
    assert permission.name == "Test Create"
    assert permission.module == "test"
    assert permission.action == "create"
    assert permission.description == "Test permission description"
    assert permission.is_active is True


@pytest.mark.asyncio
async def test_get_permission(db_session: AsyncSession):
    """Test get permission by ID."""
    permission_in = PermissionCreate(
        code="test:get",
        name="Test Get",
        module="test",
        action="read",
        description="Test get permission",
        is_active=True
    )
    created = await crud_permission.create(db_session, obj_in=permission_in)

    retrieved = await crud_permission.get(db_session, id=created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.code == "test:get"
    assert retrieved.name == "Test Get"


@pytest.mark.asyncio
async def test_get_permission_not_found(db_session: AsyncSession):
    """Test get permission by ID that does not exist."""
    result = await crud_permission.get(db_session, id=99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_multi_permissions(db_session: AsyncSession):
    """Test get multiple permissions with pagination."""
    permission1 = PermissionCreate(
        code="test:list:1",
        name="Test List 1",
        module="test",
        action="read",
        is_active=True
    )
    permission2 = PermissionCreate(
        code="test:list:2",
        name="Test List 2",
        module="test",
        action="read",
        is_active=True
    )
    await crud_permission.create(db_session, obj_in=permission1)
    await crud_permission.create(db_session, obj_in=permission2)

    permissions = await crud_permission.get_multi(db_session, skip=0, limit=10)

    assert len(permissions) >= 2


@pytest.mark.asyncio
async def test_get_multi_permissions_pagination(db_session: AsyncSession):
    """Test get multiple permissions with pagination."""
    for i in range(5):
        permission = PermissionCreate(
            code=f"test:page:{i}",
            name=f"Test Page {i}",
            module="pagination",
            action="read",
            is_active=True
        )
        await crud_permission.create(db_session, obj_in=permission)

    first_page = await crud_permission.get_multi(db_session, skip=0, limit=2)
    assert len(first_page) == 2

    second_page = await crud_permission.get_multi(db_session, skip=2, limit=2)
    assert len(second_page) == 2


@pytest.mark.asyncio
async def test_get_by_code(db_session: AsyncSession):
    """Test get permission by code."""
    permission_in = PermissionCreate(
        code="test:unique:code",
        name="Test By Code",
        module="test",
        action="write",
        is_active=True
    )
    await crud_permission.create(db_session, obj_in=permission_in)

    result = await crud_permission.get_by_code(db_session, code="test:unique:code")

    assert result is not None
    assert result.code == "test:unique:code"
    assert result.name == "Test By Code"


@pytest.mark.asyncio
async def test_get_by_code_not_found(db_session: AsyncSession):
    """Test get permission by code that does not exist."""
    result = await crud_permission.get_by_code(db_session, code="nonexistent:code")
    assert result is None


@pytest.mark.asyncio
async def test_get_by_module(db_session: AsyncSession):
    """Test get permissions by module."""
    permission1 = PermissionCreate(
        code="user:read:1",
        name="User Read 1",
        module="user",
        action="read",
        is_active=True
    )
    permission2 = PermissionCreate(
        code="user:write:1",
        name="User Write 1",
        module="user",
        action="write",
        is_active=True
    )
    permission3 = PermissionCreate(
        code="role:read:1",
        name="Role Read 1",
        module="role",
        action="read",
        is_active=True
    )
    await crud_permission.create(db_session, obj_in=permission1)
    await crud_permission.create(db_session, obj_in=permission2)
    await crud_permission.create(db_session, obj_in=permission3)

    user_permissions = await crud_permission.get_by_module(db_session, module="user")

    assert len(user_permissions) == 2
    for perm in user_permissions:
        assert perm.module == "user"


@pytest.mark.asyncio
async def test_get_active_permissions(db_session: AsyncSession):
    """Test get active permissions."""
    active_permission = PermissionCreate(
        code="test:active",
        name="Test Active",
        module="test",
        action="read",
        is_active=True
    )
    inactive_permission = PermissionCreate(
        code="test:inactive",
        name="Test Inactive",
        module="test",
        action="write",
        is_active=False
    )
    await crud_permission.create(db_session, obj_in=active_permission)
    await crud_permission.create(db_session, obj_in=inactive_permission)

    active_permissions = await crud_permission.get_active_permissions(db_session)

    for perm in active_permissions:
        assert perm.is_active is True


@pytest.mark.asyncio
async def test_get_multi_with_filters(db_session: AsyncSession):
    """Test get permissions with filters."""
    permission1 = PermissionCreate(
        code="filter:active:user",
        name="Filter Active User",
        module="user",
        action="read",
        is_active=True
    )
    permission2 = PermissionCreate(
        code="filter:inactive:user",
        name="Filter Inactive User",
        module="user",
        action="write",
        is_active=False
    )
    permission3 = PermissionCreate(
        code="filter:active:role",
        name="Filter Active Role",
        module="role",
        action="read",
        is_active=True
    )
    await crud_permission.create(db_session, obj_in=permission1)
    await crud_permission.create(db_session, obj_in=permission2)
    await crud_permission.create(db_session, obj_in=permission3)

    permissions, total = await crud_permission.get_multi_with_filters(
        db_session, module="user", is_active=True
    )

    assert total == 1
    assert len(permissions) == 1
    assert permissions[0].module == "user"
    assert permissions[0].is_active is True


@pytest.mark.asyncio
async def test_get_modules(db_session: AsyncSession):
    """Test get all distinct permission modules."""
    permission1 = PermissionCreate(
        code="modules:user:1",
        name="Modules User 1",
        module="user",
        action="read",
        is_active=True
    )
    permission2 = PermissionCreate(
        code="modules:role:1",
        name="Modules Role 1",
        module="role",
        action="read",
        is_active=True
    )
    permission3 = PermissionCreate(
        code="modules:user:2",
        name="Modules User 2",
        module="user",
        action="write",
        is_active=True
    )
    await crud_permission.create(db_session, obj_in=permission1)
    await crud_permission.create(db_session, obj_in=permission2)
    await crud_permission.create(db_session, obj_in=permission3)

    modules = await crud_permission.get_modules(db_session)

    assert len(modules) == 2
    assert "user" in modules
    assert "role" in modules
