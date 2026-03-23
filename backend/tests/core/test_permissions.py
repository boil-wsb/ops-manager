"""
Tests for permission checking functions in app.core.permissions.
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.core.permissions import (
    get_user_permissions,
    has_permission,
    has_any_permission,
    has_all_permissions,
    PermissionChecker,
    require_permissions,
    check_permission,
)


def create_mock_user(is_superuser: bool = False, roles: list = None) -> MagicMock:
    """Create a mock user with roles."""
    user = MagicMock()
    user.is_superuser = is_superuser
    user.roles = roles or []
    return user


def create_mock_role(is_active: bool, permissions: list = None) -> MagicMock:
    """Create a mock role with permissions."""
    role = MagicMock()
    role.is_active = is_active
    role.permissions = permissions or []
    return role


def create_mock_permission(code: str, is_active: bool = True) -> MagicMock:
    """Create a mock permission."""
    perm = MagicMock()
    perm.code = code
    perm.is_active = is_active
    return perm


class TestGetUserPermissions:
    """Tests for get_user_permissions function."""

    def test_superuser_returns_wildcard(self):
        """Test that superuser gets wildcard permission."""
        user = create_mock_user(is_superuser=True)
        result = get_user_permissions(user)
        assert result == ["*"]

    def test_user_with_no_roles(self):
        """Test user with no roles returns empty list."""
        user = create_mock_user(is_superuser=False, roles=[])
        result = get_user_permissions(user)
        assert result == []

    def test_user_with_inactive_role(self):
        """Test that inactive roles are excluded."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=False, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        result = get_user_permissions(user)
        assert result == []

    def test_user_with_active_role_and_permission(self):
        """Test user with active role and permission."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        result = get_user_permissions(user)
        assert "test:read" in result

    def test_user_with_inactive_permission(self):
        """Test that inactive permissions are excluded."""
        perm = create_mock_permission("test:read", is_active=False)
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        result = get_user_permissions(user)
        assert "test:read" not in result

    def test_user_with_multiple_roles_and_permissions(self):
        """Test user with multiple roles and permissions."""
        perm1 = create_mock_permission("user:read")
        perm2 = create_mock_permission("user:write")
        perm3 = create_mock_permission("role:read")

        role1 = create_mock_role(is_active=True, permissions=[perm1, perm2])
        role2 = create_mock_role(is_active=True, permissions=[perm3])

        user = create_mock_user(is_superuser=False, roles=[role1, role2])

        result = get_user_permissions(user)
        assert len(result) == 3
        assert "user:read" in result
        assert "user:write" in result
        assert "role:read" in result

    def test_duplicate_permissions_from_multiple_roles(self):
        """Test that duplicate permissions are deduplicated."""
        perm = create_mock_permission("user:read")

        role1 = create_mock_role(is_active=True, permissions=[perm])
        role2 = create_mock_role(is_active=True, permissions=[perm])

        user = create_mock_user(is_superuser=False, roles=[role1, role2])

        result = get_user_permissions(user)
        assert result.count("user:read") == 1


class TestHasPermission:
    """Tests for has_permission function."""

    def test_superuser_always_has_permission(self):
        """Test that superuser always returns True."""
        user = create_mock_user(is_superuser=True)
        assert has_permission(user, "any:permission") is True

    def test_user_without_permission(self):
        """Test user without the required permission."""
        user = create_mock_user(is_superuser=False, roles=[])
        assert has_permission(user, "test:read") is False

    def test_user_with_specific_permission(self):
        """Test user with specific permission."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        assert has_permission(user, "test:read") is True

    def test_user_with_wildcard_permission(self):
        """Test user with wildcard permission can access anything."""
        user = create_mock_user(is_superuser=False, roles=[])
        user.roles = []

        perm_wildcard = create_mock_permission("*")
        role = create_mock_role(is_active=True, permissions=[perm_wildcard])
        user.roles = [role]

        assert has_permission(user, "test:read") is True
        assert has_permission(user, "test:write") is True
        assert has_permission(user, "anything:at:all") is True


class TestHasAnyPermission:
    """Tests for has_any_permission function."""

    def test_superuser_always_has_any_permission(self):
        """Test that superuser always returns True."""
        user = create_mock_user(is_superuser=True)
        assert has_any_permission(user, ["test:read", "test:write"]) is True

    def test_user_with_one_matching_permission(self):
        """Test user with at least one matching permission."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        assert has_any_permission(user, ["test:read", "test:write"]) is True

    def test_user_with_no_matching_permissions(self):
        """Test user with no matching permissions."""
        perm = create_mock_permission("other:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        assert has_any_permission(user, ["test:read", "test:write"]) is False

    def test_empty_permission_list(self):
        """Test with empty permission list."""
        user = create_mock_user(is_superuser=False, roles=[])
        assert has_any_permission(user, []) is False


class TestHasAllPermissions:
    """Tests for has_all_permissions function."""

    def test_superuser_always_has_all_permissions(self):
        """Test that superuser always returns True."""
        user = create_mock_user(is_superuser=True)
        assert has_all_permissions(user, ["test:read", "test:write"]) is True

    def test_user_with_all_permissions(self):
        """Test user with all required permissions."""
        perm1 = create_mock_permission("test:read")
        perm2 = create_mock_permission("test:write")
        role = create_mock_role(is_active=True, permissions=[perm1, perm2])
        user = create_mock_user(is_superuser=False, roles=[role])

        assert has_all_permissions(user, ["test:read", "test:write"]) is True

    def test_user_with_missing_permission(self):
        """Test user missing one required permission."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        assert has_all_permissions(user, ["test:read", "test:write"]) is False

    def test_empty_permission_list(self):
        """Test with empty permission list."""
        user = create_mock_user(is_superuser=False, roles=[])
        assert has_all_permissions(user, []) is True


class TestPermissionChecker:
    """Tests for PermissionChecker class."""

    def test_superuser_passes_check(self):
        """Test that superuser passes permission check."""
        user = create_mock_user(is_superuser=True)
        checker = PermissionChecker(["test:read"])
        result = checker(user)
        assert result is None

    def test_user_has_required_permission(self):
        """Test user with required permission passes check."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        checker = PermissionChecker(["test:read"])
        result = checker(user)
        assert result is None

    def test_user_missing_required_permission_raises_exception(self):
        """Test user without required permission raises HTTPException."""
        user = create_mock_user(is_superuser=False, roles=[])
        checker = PermissionChecker(["test:read"])

        with pytest.raises(HTTPException) as exc_info:
            checker(user)

        assert exc_info.value.status_code == 403
        assert "test:read" in exc_info.value.detail

    def test_checker_with_any_permission_mode(self):
        """Test checker with require_all=False (any permission)."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        checker = PermissionChecker(["test:read", "test:write"], require_all=False)
        result = checker(user)
        assert result is None

    def test_checker_with_all_permission_mode(self):
        """Test checker with require_all=True (all permissions)."""
        perm1 = create_mock_permission("test:read")
        perm2 = create_mock_permission("test:write")
        role = create_mock_role(is_active=True, permissions=[perm1, perm2])
        user = create_mock_user(is_superuser=False, roles=[role])

        checker = PermissionChecker(["test:read", "test:write"], require_all=True)
        result = checker(user)
        assert result is None

    def test_checker_require_all_fails_when_one_missing(self):
        """Test require_all=True fails when one permission is missing."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        checker = PermissionChecker(["test:read", "test:write"], require_all=True)

        with pytest.raises(HTTPException) as exc_info:
            checker(user)

        assert exc_info.value.status_code == 403


class TestRequirePermissions:
    """Tests for require_permissions function."""

    def test_returns_permission_checker(self):
        """Test that require_permissions returns a PermissionChecker."""
        checker = require_permissions(["test:read"])
        assert isinstance(checker, PermissionChecker)

    def test_checker_with_require_all_false(self):
        """Test require_permissions with require_all=False."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        checker = require_permissions(["test:read", "test:write"], require_all=False)
        result = checker(user)
        assert result is None

    def test_checker_with_require_all_true(self):
        """Test require_permissions with require_all=True."""
        perm1 = create_mock_permission("test:read")
        perm2 = create_mock_permission("test:write")
        role = create_mock_role(is_active=True, permissions=[perm1, perm2])
        user = create_mock_user(is_superuser=False, roles=[role])

        checker = require_permissions(["test:read", "test:write"], require_all=True)
        result = checker(user)
        assert result is None


class TestCheckPermission:
    """Tests for check_permission function."""

    def test_superuser_passes_check(self):
        """Test that superuser passes check_permission."""
        user = create_mock_user(is_superuser=True)
        result = check_permission(user, "test:read")
        assert result is None

    def test_user_with_permission_passes(self):
        """Test user with permission passes check."""
        perm = create_mock_permission("test:read")
        role = create_mock_role(is_active=True, permissions=[perm])
        user = create_mock_user(is_superuser=False, roles=[role])

        result = check_permission(user, "test:read")
        assert result is None

    def test_user_without_permission_raises_exception(self):
        """Test user without permission raises HTTPException."""
        user = create_mock_user(is_superuser=False, roles=[])

        with pytest.raises(HTTPException) as exc_info:
            check_permission(user, "test:read")

        assert exc_info.value.status_code == 403
        assert "test:read" in exc_info.value.detail
