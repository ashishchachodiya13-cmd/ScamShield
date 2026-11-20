import time
from typing import Dict, List, Tuple, Optional
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter.
    Self-contained, thread-safe for asyncio, and directly unit-testable.
    """

    def __init__(self):
        # key -> list of timestamp floats
        self._records: Dict[str, List[float]] = {}

    def check(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Checks if the request is within limits.
        If allowed, records the hit and returns (True, 0).
        If exceeded, returns (False, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        timestamps = self._records.get(key, [])
        # Filter out timestamps outside the sliding window
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if len(valid_timestamps) >= limit:
            # Oldest timestamp that would drop out
            oldest = valid_timestamps[0]
            retry_after = max(1, int(oldest + window_seconds - now))
            self._records[key] = valid_timestamps
            return False, retry_after

        valid_timestamps.append(now)
        self._records[key] = valid_timestamps
        return True, 0

    def reset(self, key: Optional[str] = None) -> None:
        """Resets a specific key or all recorded timestamps."""
        if key:
            self._records.pop(key, None)
        else:
            self._records.clear()

    def get_client_ip(self, request: Request) -> str:
        """Extracts client IP from headers or client host."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"


# Default singleton instance
limiter = InMemoryRateLimiter()


def enforce_rate_limit(request: Request, key_prefix: str, limit: int, window_seconds: int, extra_key: str = ""):
    """Helper to enforce rate limits on FastAPI routes, raising 429 if exceeded."""
    ip = limiter.get_client_ip(request)
    composite_key = f"{key_prefix}:{ip}:{extra_key}".rstrip(":")
    allowed, retry_after = limiter.check(composite_key, limit, window_seconds)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
