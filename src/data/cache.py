"""Simple file-based cache for API responses.

Prevents redundant API calls within the same run and across
morning/evening runs on the same day. Respects Alpha Vantage's
25 calls/day free-tier limit.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

log = get_logger(__name__)

# Cache directory within the project
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache"


class FileCache:
    """A simple file-based cache with TTL expiration."""

    def __init__(self, cache_dir: Path | None = None, default_ttl: int = 3600):
        """Initialize the cache.

        Args:
            cache_dir: Directory to store cache files.
            default_ttl: Default time-to-live in seconds (1 hour).
        """
        self.cache_dir = cache_dir or _CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

    def _key_to_path(self, key: str) -> Path:
        """Convert a cache key to a file path."""
        hashed = hashlib.sha256(key.encode()).hexdigest()[:16]
        safe_key = "".join(c if c.isalnum() else "_" for c in key)[:50]
        return self.cache_dir / f"{safe_key}_{hashed}.json"

    def get(self, key: str) -> Any | None:
        """Retrieve a cached value if it exists and hasn't expired.

        Args:
            key: Cache key string.

        Returns:
            Cached data or None if not found / expired.
        """
        path = self._key_to_path(key)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            if time.time() > data.get("expires_at", 0):
                path.unlink(missing_ok=True)
                log.debug("cache_expired", key=key)
                return None
            log.debug("cache_hit", key=key)
            return data["value"]
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key string.
            value: Data to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds. Uses default if not specified.
        """
        ttl = ttl if ttl is not None else self.default_ttl
        path = self._key_to_path(key)
        data = {
            "value": value,
            "created_at": time.time(),
            "expires_at": time.time() + ttl,
        }
        path.write_text(json.dumps(data, default=str))
        log.debug("cache_set", key=key, ttl=ttl)

    def clear(self) -> int:
        """Remove all cached files.

        Returns:
            Number of files removed.
        """
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        log.info("cache_cleared", files_removed=count)
        return count


# Module-level singleton for convenience
cache = FileCache()
