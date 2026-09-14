"""Fixture replay for provider tests."""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime
from typing import cast

import aiohttp
import pytest

from pyopentides.provider import TideProvider
from pyopentides.providers import PROVIDERS

from .fakesession import FakeSession

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

# Must match what was recorded. See fixtures/README.md.
START = datetime(2026, 9, 14, tzinfo=UTC)
END = datetime(2026, 9, 21, tzinfo=UTC)
CURVE_END = datetime(2026, 9, 16, tzinfo=UTC)
NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def load_fixture(slug: str, session: FakeSession) -> None:
    d = FIXTURES / slug
    for rec in json.loads((d / "requests.json").read_text()):
        session.add(rec["url"], rec["status"], (d / rec["body"]).read_text())


@pytest.fixture
def fake() -> FakeSession:
    return FakeSession()


@pytest.fixture
def session(fake: FakeSession) -> aiohttp.ClientSession:
    return cast(aiohttp.ClientSession, fake)


def make_provider(slug: str, fake: FakeSession) -> TideProvider:
    load_fixture(slug, fake)
    provider = PROVIDERS[slug](cast(aiohttp.ClientSession, fake), version="test")
    provider._now = staticmethod(lambda: NOW)  # type: ignore[method-assign]
    return provider
