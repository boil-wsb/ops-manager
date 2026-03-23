"""
Tests for CRUDBase class.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.navigation import NavigationLink
from app.schemas.navigation import NavigationLinkCreate, NavigationLinkUpdate


@pytest.fixture
def crud_navigation() -> CRUDBase:
    """CRUDBase instance for NavigationLink."""
    return CRUDBase(NavigationLink)


@pytest.fixture
async def sample_navigation(db_session: AsyncSession, crud_navigation: CRUDBase) -> NavigationLink:
    """Create a sample navigation link for testing."""
    obj_in = NavigationLinkCreate(
        category="test_category",
        name="test_link",
        url="https://example.com",
        icon="icon",
        description="test description",
        sort_order=1,
        is_active=True
    )
    return await crud_navigation.create(db_session, obj_in=obj_in)


@pytest.mark.asyncio
async def test_get(db_session: AsyncSession, crud_navigation: CRUDBase, sample_navigation: NavigationLink):
    """Test get method with valid ID."""
    result = await crud_navigation.get(db_session, id=sample_navigation.id)
    assert result is not None
    assert result.id == sample_navigation.id
    assert result.name == "test_link"
    assert result.category == "test_category"


@pytest.mark.asyncio
async def test_get_invalid_id(db_session: AsyncSession, crud_navigation: CRUDBase):
    """Test get method with invalid ID."""
    result = await crud_navigation.get(db_session, id=99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_multi(db_session: AsyncSession, crud_navigation: CRUDBase):
    """Test get_multi method with pagination."""
    for i in range(5):
        obj_in = NavigationLinkCreate(
            category=f"cat_{i}",
            name=f"link_{i}",
            url=f"https://example{i}.com",
            sort_order=i,
            is_active=True
        )
        await crud_navigation.create(db_session, obj_in=obj_in)

    result = await crud_navigation.get_multi(db_session, skip=0, limit=3)
    assert len(result) == 3

    result_skip = await crud_navigation.get_multi(db_session, skip=3, limit=10)
    assert len(result_skip) == 2


@pytest.mark.asyncio
async def test_get_multi_default_params(db_session: AsyncSession, crud_navigation: CRUDBase):
    """Test get_multi with default parameters."""
    result = await crud_navigation.get_multi(db_session)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_create(db_session: AsyncSession, crud_navigation: CRUDBase):
    """Test create method."""
    obj_in = NavigationLinkCreate(
        category="new_category",
        name="new_link",
        url="https://new.example.com",
        icon="new_icon",
        description="new description",
        sort_order=10,
        is_active=True
    )
    result = await crud_navigation.create(db_session, obj_in=obj_in)

    assert result.id is not None
    assert result.category == "new_category"
    assert result.name == "new_link"
    assert result.url == "https://new.example.com"
    assert result.icon == "new_icon"
    assert result.sort_order == 10
    assert result.is_active is True


@pytest.mark.asyncio
async def test_update(db_session: AsyncSession, crud_navigation: CRUDBase, sample_navigation: NavigationLink):
    """Test update method with schema."""
    obj_in = NavigationLinkUpdate(name="updated_name", is_active=False)
    result = await crud_navigation.update(db_session, db_obj=sample_navigation, obj_in=obj_in)

    assert result.name == "updated_name"
    assert result.is_active is False
    assert result.category == sample_navigation.category


@pytest.mark.asyncio
async def test_update_with_dict(db_session: AsyncSession, crud_navigation: CRUDBase, sample_navigation: NavigationLink):
    """Test update method with dictionary."""
    update_data = {"name": "dict_updated_name", "url": "https://updated.example.com"}
    result = await crud_navigation.update(db_session, db_obj=sample_navigation, obj_in=update_data)

    assert result.name == "dict_updated_name"
    assert result.url == "https://updated.example.com"


@pytest.mark.asyncio
async def test_delete(db_session: AsyncSession, crud_navigation: CRUDBase, sample_navigation: NavigationLink):
    """Test delete method."""
    navigation_id = sample_navigation.id
    result = await crud_navigation.delete(db_session, id=navigation_id)

    assert result is not None
    assert result.id == navigation_id

    check_deleted = await crud_navigation.get(db_session, id=navigation_id)
    assert check_deleted is None


@pytest.mark.asyncio
async def test_delete_invalid_id(db_session: AsyncSession, crud_navigation: CRUDBase):
    """Test delete method with invalid ID."""
    result = await crud_navigation.delete(db_session, id=99999)
    assert result is None
