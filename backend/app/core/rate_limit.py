"""
Rate limiter configuration.
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

if os.environ.get("DISABLE_RATE_LIMIT", "false").lower() == "true":
    limiter = Limiter(key_func=get_remote_address, default_limits=["10000/minute"])
else:
    limiter = Limiter(key_func=get_remote_address)
