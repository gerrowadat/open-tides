"""Shared fixtures for HA integration tests.

A fake provider is registered under two slugs so tests never touch the
network and are independent of provider quirks.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.open_tides.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PROVIDER,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    DOMAIN,
)
from pyopentides import (
    Capabilities,
    Location,
    Observation,
    Point,
    Station,
    TideEvent,
    TideProvider,
)
from pyopentides.providers import PROVIDERS

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
HALF_CYCLE = timedelta(hours=6, minutes=12)


def make_events(start: datetime, end: datetime) -> list[TideEvent]:
    """Alternating high/low every 6h12m, starting with a high at 03:00 on day 1."""
    t = datetime(2026, 9, 13, 3, 0, tzinfo=UTC)
    kind = "high"
    out: list[TideEvent] = []
    while t <= end:
        if t >= start:
            out.append(
                TideEvent(time=t, height_m=4.0 if kind == "high" else 0.5, kind=kind)
            )
        t += HALF_CYCLE
        kind = "low" if kind == "high" else "high"
    return out


def make_curve(start: datetime, end: datetime) -> list[Point]:
    """Straight ramp 1.0 → 3.0 across the window; easy to interpolate by hand."""
    n = int((end - start) / timedelta(minutes=10))
    return [
        Point(time=start + timedelta(minutes=10 * i), height_m=1.0 + 2.0 * i / n)
        for i in range(n + 1)
    ]


class FakeProvider(TideProvider):
    slug = "fake"
    name = "Fake Hydrographic Office"
    attribution = "Fake data (test)"
    licence = "CC-BY-4.0"
    licence_url = "https://creativecommons.org/licenses/by/4.0/"
    datum = "LAT"
    coordinate_based = False
    min_refresh = timedelta(hours=12)
    horizon = timedelta(days=30)
    supports_curve = True
    supports_observed = True
    observed_min_refresh = timedelta(minutes=10)

    calls: dict[str, int] = {}  # noqa: RUF012 - reset per test by fixture
    caps = Capabilities(curve=True, observed=True)
    observation: Observation | None = Observation(
        time=NOW - timedelta(minutes=5), height_m=2.5
    )

    def _count(self, name: str) -> None:
        FakeProvider.calls[name] = FakeProvider.calls.get(name, 0) + 1

    async def list_stations(self) -> list[Station] | None:
        self._count("list_stations")
        return [
            Station(id="st1", name="Testport", lat=53.0, lon=-6.0),
            Station(id="st2", name="Otherport", lat=54.0, lon=-7.0),
        ]

    async def capabilities(self, loc: Location) -> Capabilities:
        self._count("capabilities")
        return FakeProvider.caps

    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        self._count("get_events")
        return make_events(start, end)

    async def get_curve(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[Point]:
        self._count("get_curve")
        return make_curve(start, end)

    async def get_observed(self, loc: Location) -> Observation | None:
        self._count("get_observed")
        return FakeProvider.observation


class FakeCoordProvider(FakeProvider):
    slug = "fake_coords"
    name = "Fake Coordinate Office"
    coordinate_based = True

    async def list_stations(self) -> list[Station] | None:
        return None


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom_components/ in every test."""


@pytest.fixture(autouse=True)
def fake_providers(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    FakeProvider.calls = {}
    FakeProvider.caps = Capabilities(curve=True, observed=True)
    FakeProvider.observation = Observation(
        time=NOW - timedelta(minutes=5), height_m=2.5
    )
    monkeypatch.setitem(PROVIDERS, "fake", FakeProvider)
    monkeypatch.setitem(PROVIDERS, "fake_coords", FakeCoordProvider)
    yield


def station_entry(options: dict[str, Any] | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Testport",
        unique_id="fake:st1",
        data={
            CONF_PROVIDER: "fake",
            CONF_STATION_ID: "st1",
            CONF_STATION_NAME: "Testport",
            CONF_LATITUDE: 53.0,
            CONF_LONGITUDE: -6.0,
        },
        options=options or {},
        version=1,
        minor_version=1,
    )
