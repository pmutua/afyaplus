"""Behavioral tests for API and Chainlit abuse prevention."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.agent.agent import create_agent
from app.chainlit_app import _ui_rate_limit_message
from app.main import create_app
from app.safeguards.rate_limiting import (
    DAY_SECONDS,
    InMemoryRateLimiter,
    RateLimitConfigurationError,
    RateLimitSettings,
    load_rate_limit_settings,
)


@dataclass
class Clock:
    now: float = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _settings(*, trust_railway_proxy: bool = False) -> RateLimitSettings:
    return RateLimitSettings(
        requests_per_minute=1,
        requests_per_day=2,
        trust_railway_proxy=trust_railway_proxy,
    )


def _test_client(settings: RateLimitSettings, responses: int = 1) -> TestClient:
    model = FakeMessagesListChatModel(
        responses=[AIMessage(content="Karibu") for _ in range(responses)]
    )
    agent = create_agent(model, [], "You are a test assistant.")
    return TestClient(
        create_app(agent, mount_ui=False, rate_limit_settings=settings)
    )


def _chat(client: TestClient, header_ip: str = "198.51.100.10"):
    thread_id = f"session-{header_ip.replace('.', '-')}"
    return client.post(
        "/chat",
        headers={"X-Real-IP": header_ip},
        json={"message": "Habari", "thread_id": thread_id},
    )


def test_limiter_blocks_then_resets_rolling_windows() -> None:
    clock = Clock()
    limiter = InMemoryRateLimiter(_settings(), clock)

    assert limiter.check("+254712345678").allowed is True
    assert limiter.check("+254712345678").retry_after_seconds == 60
    clock.advance(61)
    assert limiter.check("+254712345678").allowed is True
    assert limiter.check("+254712345678").retry_after_seconds == DAY_SECONDS - 61
    clock.advance(DAY_SECONDS)
    assert limiter.check("+254712345678").allowed is True


def test_api_ignores_proxy_header_when_railway_trust_is_disabled() -> None:
    client = _test_client(_settings())

    assert _chat(client, "198.51.100.10").status_code == 200
    blocked = _chat(client, "203.0.113.20")

    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"
    assert "+254" not in blocked.text


def test_api_uses_railway_client_ip_only_when_trust_is_enabled() -> None:
    client = _test_client(_settings(trust_railway_proxy=True), responses=2)

    assert _chat(client, "198.51.100.10").status_code == 200
    assert _chat(client, "203.0.113.20").status_code == 200
    assert _chat(client, "198.51.100.10").status_code == 429
    assert client.get("/health").status_code == 200


def test_chainlit_limits_each_session_before_model_use() -> None:
    limiter = InMemoryRateLimiter(_settings(), Clock())

    assert _ui_rate_limit_message("ui-session", limiter) is None
    message = _ui_rate_limit_message("ui-session", limiter)

    assert message == "Too many requests. Try again in 60 seconds."
    assert _ui_rate_limit_message("other-session", limiter) is None


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("RATE_LIMIT_REQUESTS_PER_MINUTE", "0"),
        ("RATE_LIMIT_REQUESTS_PER_DAY", "invalid"),
        ("RATE_LIMIT_ENABLED", "sometimes"),
    ],
)
def test_invalid_rate_limit_configuration_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(RateLimitConfigurationError, match=name):
        load_rate_limit_settings()
