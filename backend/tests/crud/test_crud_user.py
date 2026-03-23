"""
Tests for CRUDUser.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.crud.crud_user import crud_user
from app.schemas.user import UserCreate, UserUpdate


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test creating a user with hashed password."""
    user_in = UserCreate(
        username="testuser1",
        email="test1@example.com",
        full_name="Test User",
        password="password123"
    )
    user = await crud_user.create(db_session, obj_in=user_in)

    assert user.id is not None
    assert user.username == "testuser1"
    assert user.email == "test1@example.com"
    assert user.full_name == "Test User"
    assert user.is_active is True
    assert user.hashed_password != "password123"
    assert verify_password("password123", user.hashed_password) is True


@pytest.mark.asyncio
async def test_create_user_with_roles(db_session: AsyncSession):
    """Test creating a user and assigning roles."""
    from app.crud.crud_role import crud_role
    from app.schemas.permission import RoleCreate

    role1 = await crud_role.create(
        db_session,
        obj_in=RoleCreate(name="Role1", description="Test role 1")
    )
    role2 = await crud_role.create(
        db_session,
        obj_in=RoleCreate(name="Role2", description="Test role 2")
    )

    user_in = UserCreate(
        username="testuser2",
        email="test2@example.com",
        full_name="Test User 2",
        password="password123",
        role_ids=[role1.id, role2.id]
    )
    user = await crud_user.create(db_session, obj_in=user_in)

    assert user.id is not None
    assert len(user.roles) == 2
    role_names = [r.name for r in user.roles]
    assert "Role1" in role_names
    assert "Role2" in role_names


@pytest.mark.asyncio
async def test_get_by_username(db_session: AsyncSession):
    """Test getting a user by username."""
    user_in = UserCreate(
        username="findme",
        email="findme@example.com",
        full_name="Find Me",
        password="password123"
    )
    await crud_user.create(db_session, obj_in=user_in)

    user = await crud_user.get_by_username(db_session, username="findme")

    assert user is not None
    assert user.username == "findme"
    assert user.email == "findme@example.com"


@pytest.mark.asyncio
async def test_get_by_username_not_found(db_session: AsyncSession):
    """Test getting a non-existent user by username."""
    user = await crud_user.get_by_username(db_session, username="nonexistent")
    assert user is None


@pytest.mark.asyncio
async def test_get_by_email(db_session: AsyncSession):
    """Test getting a user by email."""
    user_in = UserCreate(
        username="emailuser",
        email="uniqueemail@example.com",
        full_name="Email User",
        password="password123"
    )
    await crud_user.create(db_session, obj_in=user_in)

    user = await crud_user.get_by_email(db_session, email="uniqueemail@example.com")

    assert user is not None
    assert user.email == "uniqueemail@example.com"
    assert user.username == "emailuser"


@pytest.mark.asyncio
async def test_get_by_email_not_found(db_session: AsyncSession):
    """Test getting a non-existent user by email."""
    user = await crud_user.get_by_email(db_session, email="nonexistent@example.com")
    assert user is None


@pytest.mark.asyncio
async def test_update_user(db_session: AsyncSession):
    """Test updating user fields."""
    user_in = UserCreate(
        username="updateuser",
        email="update@example.com",
        full_name="Original Name",
        password="password123"
    )
    user = await crud_user.create(db_session, obj_in=user_in)

    update_data = UserUpdate(full_name="Updated Name", email="updated@example.com")
    updated_user = await crud_user.update(db_session, db_obj=user, obj_in=update_data)

    assert updated_user.full_name == "Updated Name"
    assert updated_user.email == "updated@example.com"
    assert updated_user.username == "updateuser"


@pytest.mark.asyncio
async def test_update_user_with_password(db_session: AsyncSession):
    """Test updating user password (should hash it)."""
    user_in = UserCreate(
        username="passuser",
        email="pass@example.com",
        full_name="Password User",
        password="oldpassword123"
    )
    user = await crud_user.create(db_session, obj_in=user_in)
    old_hash = user.hashed_password

    update_data = UserUpdate(password="newpassword456")
    updated_user = await crud_user.update(db_session, db_obj=user, obj_in=update_data)

    assert updated_user.hashed_password != "newpassword456"
    assert updated_user.hashed_password != old_hash
    assert verify_password("newpassword456", updated_user.hashed_password) is True


@pytest.mark.asyncio
async def test_update_user_with_roles(db_session: AsyncSession):
    """Test updating user roles."""
    from app.crud.crud_role import crud_role
    from app.schemas.permission import RoleCreate

    role1 = await crud_role.create(
        db_session,
        obj_in=RoleCreate(name="UpdateRole1", description="Test")
    )
    role2 = await crud_role.create(
        db_session,
        obj_in=RoleCreate(name="UpdateRole2", description="Test")
    )
    role3 = await crud_role.create(
        db_session,
        obj_in=RoleCreate(name="UpdateRole3", description="Test")
    )

    user_in = UserCreate(
        username="roleuser",
        email="role@example.com",
        full_name="Role User",
        password="password123",
        role_ids=[role1.id]
    )
    user = await crud_user.create(db_session, obj_in=user_in)
    assert len(user.roles) == 1

    update_data = UserUpdate(role_ids=[role2.id, role3.id])
    updated_user = await crud_user.update(db_session, db_obj=user, obj_in=update_data)

    assert len(updated_user.roles) == 2
    role_names = [r.name for r in updated_user.roles]
    assert "UpdateRole2" in role_names
    assert "UpdateRole3" in role_names
