from __future__ import annotations

from dataclasses import dataclass
import logging

from fastapi import status
from fastapi.responses import JSONResponse
from redis import RedisError
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    prefix: str
    window_seconds: int
    max_requests: int


class RedisRateLimitStore:
    def __init__(self, redis_client: Redis, *, key_prefix: str) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix

    async def hit(self, *, bucket: str, subject: str, window_seconds: int, max_requests: int) -> tuple[bool, int]:
        key = f"{self._key_prefix}:rate_limit:{bucket}:{subject}"

        request_count = await self._redis.incr(key)
        ttl = await self._redis.ttl(key)

        if request_count == 1 or ttl < 0:
            await self._redis.expire(key, window_seconds)
            ttl = window_seconds

        if request_count > max_requests:
            return False, max(1, ttl)

        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._store = RedisRateLimitStore(
            Redis.from_url(settings.redis_url, decode_responses=True),
            key_prefix=settings.redis_key_prefix,
        )
        self._rules = (
            RateLimitRule(
                prefix="/api/auth/login/",
                window_seconds=settings.auth_rate_limit_window_seconds,
                max_requests=settings.auth_rate_limit_max_requests,
            ),
            RateLimitRule(
                prefix="/api/auth/signup/",
                window_seconds=settings.auth_rate_limit_window_seconds,
                max_requests=settings.auth_rate_limit_max_requests,
            ),
            RateLimitRule(
                prefix="/api/videos/upload/",
                window_seconds=settings.upload_rate_limit_window_seconds,
                max_requests=settings.upload_rate_limit_max_requests,
            ),
        )
        self._redis_error_logged = False

    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        for rule in self._rules:
            if request.url.path != rule.prefix:
                continue

            try:
                allowed, retry_after = await self._store.hit(
                    bucket=rule.prefix.strip("/").replace("/", ":"),
                    subject=client,
                    window_seconds=rule.window_seconds,
                    max_requests=rule.max_requests,
                )
            except RedisError:
                if not self._redis_error_logged:
                    logger.warning("Redis rate limiter unavailable; allowing requests until Redis recovers.")
                    self._redis_error_logged = True
                break

            if allowed:
                break

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
