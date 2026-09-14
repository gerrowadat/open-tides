"""Minimal stand-in for aiohttp.ClientSession that replays recorded responses.

Only what ``pyopentides.http.fetch_text`` uses: ``session.get(...)`` as an
async context manager with ``.status`` and ``.text()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self

import aiohttp
from yarl import URL

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass
class Recorded:
    status: int
    body: str


@dataclass
class Call:
    url: URL
    headers: dict[str, str]


@dataclass
class _Response:
    status: int
    _body: str

    async def text(self) -> str:
        return self._body

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


class _Raise:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def __aenter__(self) -> Any:
        raise self._exc

    async def __aexit__(self, *exc: object) -> None:
        return None


@dataclass
class FakeSession:
    routes: dict[URL, Recorded] = field(default_factory=dict)
    errors: dict[URL, BaseException] = field(default_factory=dict)
    calls: list[Call] = field(default_factory=list)

    def add(self, url: str, status: int, body: str) -> None:
        self.routes[URL(url)] = Recorded(status, body)

    def fail(self, url: str, exc: BaseException) -> None:
        self.errors[URL(url)] = exc

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
    ) -> Any:
        full = URL(url).with_query(dict(params)) if params else URL(url)
        self.calls.append(Call(full, dict(headers or {})))
        if full in self.errors:
            return _Raise(self.errors[full])
        rec = self.routes.get(full)
        if rec is None:
            msg = f"unrecorded request: {full}"
            raise AssertionError(msg)
        return _Response(rec.status, rec.body)

    def urls(self) -> list[str]:
        return [str(c.url) for c in self.calls]
