"""Fixture replay for provider tests."""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator
from datetime import UTC, datetime

import aiohttp
import pytest
from aioresponses import aioresponses

from pyopentides.provider import TideProvider
from pyopentides.providers import PROVIDERS

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

# Must match what was recorded. See fixtures/README.md.
START = datetime(2026, 9, 14, tzinfo=UTC)
END = datetime(2026, 9, 21, tzinfo=UTC)
CURVE_END = datetime(2026, 9, 16, tzinfo=UTC)
NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def load_fixture(slug: str, mocked: aioresponses) -> None:
    d = FIXTURES / slug
    for rec in json.loads((d / "requests.json").read_text()):
        mocked.get(
            rec["url"],
            status=rec["status"],
            body=(d / rec["body"]).read_text(),
            repeat=True,
        )


@pytest.fixture
def mocked() -> Iterator[aioresponses]:
    with aioresponses() as m:
        yield m


@pytest.fixture
async def session() -> Iterator[aiohttp.ClientSession]:
    # ThreadedResolver: the aiodns resolver leaves a pycares thread behind,
    # which the HA test plugin flags as a leak.
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as s:
        yield s


def make_provider(
    slug: str, session: aiohttp.ClientSession, mocked: aioresponses
) -> TideProvider:
    load_fixture(slug, mocked)
    provider = PROVIDERS[slug](session, version="test")
    provider._now = staticmethod(lambda: NOW)  # type: ignore[method-assign]
    return provider
