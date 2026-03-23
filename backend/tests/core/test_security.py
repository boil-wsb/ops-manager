"""
Tests for security utilities.
"""
import pytest
from datetime import timedelta

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    verify_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_generates_non_empty_hash(self):
        """Test that get_password_hash generates a non-empty hash."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert len(hashed) > 0

    def test_get_password_hash_different_from_password(self):
        """Test that the hash is different from the original password."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password

    def test_get_password_hash_different_each_time(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2


class TestPasswordVerification:
    """Tests for password verification function."""

    def test_verify_password_returns_true_for_correct_password(self):
        """Test that verify_password returns True for correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        result = verify_password(password, hashed)

        assert result is True

    def test_verify_password_returns_false_for_wrong_password(self):
        """Test that verify_password returns False for wrong password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        result = verify_password(wrong_password, hashed)

        assert result is False

    def test_verify_password_returns_false_for_invalid_hash(self):
        """Test that verify_password returns False for invalid hash."""
        result = verify_password("password", "invalid_hash")

        assert result is False


class TestAccessToken:
    """Tests for access token functions."""

    def test_create_access_token_generates_valid_token(self):
        """Test that create_access_token generates a non-empty token."""
        data = {"sub": "test_user"}
        token = create_access_token(data)

        assert token is not None
        assert len(token) > 0
        assert "." in token

    def test_create_access_token_with_custom_expiry(self):
        """Test that create_access_token respects custom expiry."""
        data = {"sub": "test_user"}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires)

        assert token is not None

    def test_decode_token_returns_data(self):
        """Test that decode_token correctly decodes token and returns data."""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["sub"] == "test_user"
        assert decoded["role"] == "admin"
        assert decoded["type"] == "access"

    def test_decode_token_returns_none_for_invalid_token(self):
        """Test that decode_token returns None for invalid token."""
        result = decode_token("invalid_token")

        assert result is None


class TestRefreshToken:
    """Tests for refresh token functions."""

    def test_create_refresh_token_generates_valid_token(self):
        """Test that create_refresh_token generates a non-empty token."""
        data = {"sub": "test_user"}
        token = create_refresh_token(data)

        assert token is not None
        assert len(token) > 0
        assert "." in token

    def test_create_refresh_token_with_custom_expiry(self):
        """Test that create_refresh_token respects custom expiry."""
        data = {"sub": "test_user"}
        expires = timedelta(days=7)
        token = create_refresh_token(data, expires_delta=expires)

        assert token is not None

    def test_refresh_token_has_refresh_type(self):
        """Test that refresh token has correct type field."""
        data = {"sub": "test_user"}
        token = create_refresh_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["type"] == "refresh"


class TestTokenVerification:
    """Tests for token verification functions."""

    def test_verify_token_type_returns_true_for_matching_type(self):
        """Test that verify_token_type returns True for matching type."""
        data = {"sub": "test_user"}
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert verify_token_type(decoded, "access") is True

    def test_verify_token_type_returns_false_for_non_matching_type(self):
        """Test that verify_token_type returns False for non-matching type."""
        data = {"sub": "test_user"}
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert verify_token_type(decoded, "refresh") is False

    def test_verify_token_is_alias_for_decode_token(self):
        """Test that verify_token returns same result as decode_token."""
        data = {"sub": "test_user"}
        token = create_access_token(data)

        result = verify_token(token)

        assert result is not None
        assert result["sub"] == "test_user"
