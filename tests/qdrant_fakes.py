from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class FakeQdrantClient:
    """Small stateful client double for application-boundary tests."""

    def __init__(self) -> None:
        self.collection_name: str | None = None
        self.created_kwargs: dict[str, Any] = {}
        self.points: list[Any] = []

    def collection_exists(self, collection_name: str) -> bool:
        return self.collection_name == collection_name

    def create_collection(self, collection_name: str, **kwargs: Any) -> bool:
        self.collection_name = collection_name
        self.created_kwargs = kwargs
        return True

    def count(self, collection_name: str, **kwargs: Any) -> SimpleNamespace:
        assert collection_name == self.collection_name
        return SimpleNamespace(count=len(self.points))

    def upload_points(
        self, collection_name: str, points: list[Any], **kwargs: Any
    ) -> None:
        assert collection_name == self.collection_name
        self.points.extend(points)

    def query_points(
        self, collection_name: str, query: Any, limit: int, **kwargs: Any
    ) -> SimpleNamespace:
        assert collection_name == self.collection_name
        query_tokens = _tokens(query.text)
        scored = [
            SimpleNamespace(payload=point.payload, score=_score(query_tokens, point))
            for point in self.points
        ]
        return SimpleNamespace(
            points=sorted(scored, key=lambda point: point.score, reverse=True)[:limit]
        )


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def _score(query_tokens: set[str], point: Any) -> float:
    text_tokens = _tokens(str(point.payload["text"]))
    return float(len(query_tokens & text_tokens))
