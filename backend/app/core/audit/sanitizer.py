"""
Data sanitizer for removing sensitive information from audit logs.
"""
import re
from typing import Any

# Sensitive fields that should be masked
SENSITIVE_FIELDS = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'access_token',
    'refresh_token', 'api_key', 'apikey', 'api_secret', 'private_key',
    'secret_key', 'auth_token', 'credentials', 'credit_card', 'cvv',
    'ssn', 'social_security', 'phone', 'mobile', 'email', 'address'
}

# Patterns for sensitive data
SENSITIVE_PATTERNS = [
    (r'\b\d{16,19}\b', '[CREDIT_CARD]'),  # Credit card numbers
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),  # SSN
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]'),  # Email
]


def sanitize_sensitive_data(data: Any) -> Any:
    """
    Recursively sanitize sensitive data from a dictionary or list.

    Args:
        data: Data to sanitize (dict, list, or primitive)

    Returns:
        Sanitized data with sensitive fields masked
    """
    if isinstance(data, dict):
        return _sanitize_dict(data)
    elif isinstance(data, list):
        return [_sanitize_value(item) for item in data]
    elif isinstance(data, str):
        return _sanitize_string(data)
    else:
        return data


def _sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a dictionary."""
    result = {}
    for key, value in data.items():
        # Check if key contains sensitive field name
        key_lower = key.lower()
        is_sensitive = any(
            sensitive in key_lower
            for sensitive in SENSITIVE_FIELDS
        )

        if is_sensitive:
            # Mask sensitive values
            result[key] = _mask_value(value)
        else:
            # Recursively sanitize non-sensitive values
            result[key] = _sanitize_value(value)

    return result


def _sanitize_value(value: Any) -> Any:
    """Sanitize a single value."""
    if isinstance(value, dict):
        return _sanitize_dict(value)
    elif isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    elif isinstance(value, str):
        return _sanitize_string(value)
    else:
        return value


def _sanitize_string(value: str) -> str:
    """Sanitize a string value using patterns."""
    result = value
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def _mask_value(value: Any) -> str:
    """Mask a sensitive value."""
    if value is None:
        return None

    if isinstance(value, str):
        if len(value) <= 4:
            return '*' * len(value)
        else:
            # Show first 2 and last 2 characters
            return value[:2] + '*' * (len(value) - 4) + value[-2:]
    elif isinstance(value, (int, float, bool)):
        return '[MASKED]'
    else:
        return '[MASKED]'


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """
    Sanitize HTTP headers by removing sensitive information.

    Args:
        headers: HTTP headers dictionary

    Returns:
        Sanitized headers
    """
    sensitive_headers = {
        'authorization', 'cookie', 'x-api-key', 'x-auth-token',
        'proxy-authorization', 'www-authenticate'
    }

    result = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in sensitive_headers:
            result[key] = '[MASKED]'
        else:
            result[key] = value

    return result
