"""
Rate limiter configuration.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

if settings.disable_rate_limit:
    limiter = Limiter(key_func=get_remote_address, default_limits=["10000/minute"])
else:
    limiter = Limiter(key_func=get_remote_address)
