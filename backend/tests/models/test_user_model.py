"""
Tests for User model.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import verify_password


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test creating a user with required fields."""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.hashed_password == "hashed_password"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_create_user_without_optional_fields(db_session: AsyncSession):
    """Test creating a user without optional fields."""
    user = User(
        username="minimaluser",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.username == "minimaluser"
    assert user.email is None
    assert user.full_name is None
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.last_login is None


@pytest.mark.asyncio
async def test_create_user_with_roles(db_session: AsyncSession):
    """Test creating a user with roles relationship."""
    from app.models.user import User
    from app.models.permission import Role

    role1 = Role(name="Admin", description="Administrator role")
    role2 = Role(name="User", description="Regular user role")
    db_session.add_all([role1, role2])
    await db_session.commit()

    user = User(
        username="roleuser",
        hashed_password="hashed_password",
        roles=[role1, role2]
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert len(user.roles) == 2
    role_names = [r.name for r in user.roles]
    assert "Admin" in role_names
    assert "User" in role_names


@pytest.mark.asyncio
async def test_user_repr(db_session: AsyncSession):
    """Test user string representation."""
    user = User(
        username="repruser",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()

    assert repr(user) == "<User repruser>"


@pytest.mark.asyncio
async def test_user_password_hashing(db_session: AsyncSession):
    """Test that password is properly stored when hashed."""
    plain_password = "securepassword123"
    hashed = verify_password.__self__.hash(plain_password) if hasattr(verify_password, '__self__') else None

    if hashed is None:
        from app.core.security import get_password_hash
        hashed = get_password_hash(plain_password)

    user = User(
        username="hashuser",
        hashed_password=hashed
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.hashed_password != plain_password
    assert verify_password(plain_password, user.hashed_password) is True
    assert verify_password("wrongpassword", user.hashed_password) is False


@pytest.mark.asyncio
async def test_user_is_active_default(db_session: AsyncSession):
    """Test that is_active defaults to True."""
    user = User(
        username="activeuser",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.is_active is True


@pytest.mark.asyncio
async def test_user_is_superuser_default(db_session: AsyncSession):
    """Test that is_superuser defaults to False."""
    user = User(
        username="superuserflag",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.is_superuser is False


@pytest.mark.asyncio
async def test_user_unique_username(db_session: AsyncSession):
    """Test that username must be unique."""
    user1 = User(
        username="uniqueuser",
        hashed_password="hashed_password"
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        username="uniqueuser",
        hashed_password="hashed_password2"
    )
    db_session.add(user2)

    with pytest.raises(Exception):
        await db_session.commit()


@pytest.mark.asyncio
async def test_user_unique_email(db_session: AsyncSession):
    """Test that email must be unique."""
    user1 = User(
        username="emailuser1",
        email="unique@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        username="emailuser2",
        email="unique@example.com",
        hashed_password="hashed_password2"
    )
    db_session.add(user2)

    with pytest.raises(Exception):
        await db_session.commit()


@pytest.mark.asyncio
async def test_user_last_login(db_session: AsyncSession):
    """Test last_login field can be set."""
    from datetime import datetime

    login_time = datetime.utcnow()
    user = User(
        username="loginuser",
        hashed_password="hashed_password",
        last_login=login_time
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.last_login is not None
    assert user.last_login == login_time
