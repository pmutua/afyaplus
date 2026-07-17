"""In-process abuse prevention for the unauthenticated chat interfaces."""

from __future__ import annotations

import hashlib
import ipaddress
import math
import os
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

MINUTE_SECONDS = 60
DAY_SECONDS = 86_400


class RateLimitConfigurationError(RuntimeError):
    """Raised when rate-limit environment settings are invalid."""


@dataclass(frozen=True)
class RateLimitSettings:
    """Resolved limits for both API clients and Chainlit sessions."""

    enabled: bool = True
    requests_per_minute: int = 10
    requests_per_day: int = 100
    trust_railway_proxy: bool = False


@dataclass(frozen=True)
class RateLimitDecision:
    """Whether a request may proceed and when a blocked client can retry."""

    allowed: bool
    retry_after_seconds: int = 0


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RateLimitConfigurationError(f"{name} must be a positive integer.") from error
    if value <= 0:
        raise RateLimitConfigurationError(f"{name} must be a positive integer.")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw_value = os.getenv(name, str(default)).strip().lower()
    if raw_value in {"true", "1", "yes", "on"}:
        return True
    if raw_value in {"false", "0", "no", "off"}:
        return False
    raise RateLimitConfigurationError(f"{name} must be true or false.")


def load_rate_limit_settings() -> RateLimitSettings:
    """Load strict rate-limit settings from the application environment."""

    load_dotenv()
    return RateLimitSettings(
        enabled=_boolean("RATE_LIMIT_ENABLED", True),
        requests_per_minute=_positive_int("RATE_LIMIT_REQUESTS_PER_MINUTE", 10),
        requests_per_day=_positive_int("RATE_LIMIT_REQUESTS_PER_DAY", 100),
        trust_railway_proxy=_boolean("RATE_LIMIT_TRUST_RAILWAY_PROXY", False),
    )


class InMemoryRateLimiter:
    """Apply rolling limits while retaining only keyed hashes and timestamps."""

    def __init__(
        self,
        settings: RateLimitSettings,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self._clock = clock
        self._salt = secrets.token_bytes(32)
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, client_key: str) -> RateLimitDecision:
        """Consume one allowance or return the rolling-window retry delay."""

        if not self.settings.enabled:
            return RateLimitDecision(allowed=True)
        now = self._clock()
        hashed_key = self._hash(client_key)
        with self._lock:
            events = self._events.setdefault(hashed_key, deque())
            self._prune(events, now)
            retry_after = self._retry_after(events, now)
            if retry_after:
                return RateLimitDecision(False, retry_after)
            events.append(now)
        return RateLimitDecision(allowed=True)

    def _hash(self, client_key: str) -> str:
        return hashlib.blake2b(
            client_key.encode("utf-8"), key=self._salt, digest_size=16
        ).hexdigest()

    @staticmethod
    def _prune(events: deque[float], now: float) -> None:
        while events and events[0] <= now - DAY_SECONDS:
            events.popleft()

    def _retry_after(self, events: deque[float], now: float) -> int:
        if len(events) >= self.settings.requests_per_day:
            return max(1, math.ceil(events[0] + DAY_SECONDS - now))
        minute_events = [stamp for stamp in events if stamp > now - MINUTE_SECONDS]
        if len(minute_events) >= self.settings.requests_per_minute:
            return max(1, math.ceil(minute_events[0] + MINUTE_SECONDS - now))
        return 0


def _socket_client(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def client_identifier(request: Request, trust_railway_proxy: bool) -> str:
    """Resolve a client IP, trusting Railway's edge header only when enabled."""

    if trust_railway_proxy:
        railway_ip = request.headers.get("x-real-ip", "").strip()
        try:
            return str(ipaddress.ip_address(railway_ip))
        except ValueError:
            pass
    return _socket_client(request)


def retry_message(retry_after_seconds: int) -> str:
    """Build the same non-sensitive retry message for API and UI clients."""

    return f"Too many requests. Try again in {retry_after_seconds} seconds."


def install_chat_rate_limiting(
    application: FastAPI,
    settings: RateLimitSettings,
    limiter: InMemoryRateLimiter | None = None,
) -> None:
    """Rate-limit POST /chat while leaving health and documentation available."""

    resolved_limiter = limiter or InMemoryRateLimiter(settings)

    @application.middleware("http")
    async def enforce_chat_limit(request: Request, call_next: Callable):  # type: ignore[no-untyped-def]
        if request.method == "POST" and request.url.path == "/chat":
            client = client_identifier(request, settings.trust_railway_proxy)
            decision = resolved_limiter.check(f"api:{client}")
            if not decision.allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": retry_message(decision.retry_after_seconds)},
                    headers={"Retry-After": str(decision.retry_after_seconds)},
                )
        return await call_next(request)
