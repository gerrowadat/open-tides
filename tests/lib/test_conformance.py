"""Conformance tests every registered provider must pass.

Assertions (docs/design.md): events sorted, UTC, metres, within range,
alternating kinds, attribution non-empty, min_refresh >= 1 h.
"""

from __future__ import annotations

from datetime import UTC, timedelta
from itertools import pairwise

import aiohttp
import pytest
from aioresponses import aioresponses

from pyopentides.exceptions import StationNotFound
from pyopentides.models import Location
from pyopentides.providers import PROVIDERS

from .conftest import CURVE_END, END, START, make_provider

# One known-good location per provider, matching the recorded fixtures.
LOCATIONS: dict[str, Location] = {
    "marine_ie": Location(station_id="Dublin_Port"),
    "noaa_coops": Location(station_id="9414290"),
    "kartverket": Location(lat=58.974339, lon=5.730121),
}
BAD: dict[str, Location] = {
    "marine_ie": Location(station_id="Nowhere"),
    "noaa_coops": Location(station_id="0000000"),
    "kartverket": Location(lat=53.3, lon=-6.2),
}

slugs = pytest.mark.parametrize("slug", sorted(PROVIDERS), ids=sorted(PROVIDERS))


def test_every_provider_has_a_fixture_location() -> None:
    assert set(LOCATIONS) == set(PROVIDERS)
    assert set(BAD) == set(PROVIDERS)


@slugs
def test_declarations(slug: str) -> None:
    cls = PROVIDERS[slug]
    assert cls.slug == slug
    assert cls.name
    assert cls.attribution
    assert cls.licence
    assert cls.licence_url.startswith("https://")
    assert cls.datum
    assert cls.min_refresh >= timedelta(hours=1)
    assert cls.horizon >= timedelta(days=7)
    if cls.supports_observed:
        assert cls.observed_min_refresh is not None
        assert cls.observed_min_refresh >= timedelta(minutes=5)


@slugs
async def test_stations_or_coordinates(
    slug: str, session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    p = make_provider(slug, session, mocked)
    stations = await p.list_stations()
    if p.coordinate_based:
        assert stations is None
    else:
        assert stations
        assert all(s.id and s.name for s in stations)
        assert all(-90 <= s.lat <= 90 and -180 <= s.lon <= 180 for s in stations)
        assert len({s.id for s in stations}) == len(stations)


@slugs
async def test_events(
    slug: str, session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    p = make_provider(slug, session, mocked)
    events = await p.get_events(LOCATIONS[slug], START, END)
    assert len(events) >= 20, "a week should hold ~26-28 events"
    for ev in events:
        assert ev.time.tzinfo is not None
        assert ev.time.utcoffset() == timedelta(0)
        assert START <= ev.time <= END
        assert -5.0 < ev.height_m < 15.0, "metres, not cm or feet"
        assert ev.kind in ("high", "low")
    times = [e.time for e in events]
    assert times == sorted(times)
    assert len(set(times)) == len(times)
    kinds = [e.kind for e in events]
    assert all(a != b for a, b in pairwise(kinds)), "alternate"


@slugs
async def test_curve(
    slug: str, session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    p = make_provider(slug, session, mocked)
    caps = await p.capabilities(LOCATIONS[slug])
    if not caps.curve:
        pytest.skip("no curve at this location")
    points = await p.get_curve(LOCATIONS[slug], START, CURVE_END)
    assert len(points) >= 48 * 2, "at least 30-min resolution"
    times = [pt.time for pt in points]
    assert times == sorted(times)
    assert len(set(times)) == len(times)
    assert all(t.tzinfo is not None and START <= t <= CURVE_END for t in times)
    assert all(-5.0 < pt.height_m < 15.0 for pt in points)


@slugs
async def test_observed(
    slug: str, session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    p = make_provider(slug, session, mocked)
    caps = await p.capabilities(LOCATIONS[slug])
    if not caps.observed:
        pytest.skip("no observations at this location")
    obs = await p.get_observed(LOCATIONS[slug])
    assert obs is not None
    assert obs.time.tzinfo is not None
    assert obs.time.astimezone(UTC) <= END
    assert -5.0 < obs.height_m < 15.0


@slugs
async def test_unknown_location(
    slug: str, session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    p = make_provider(slug, session, mocked)
    with pytest.raises(StationNotFound):
        await p.get_events(BAD[slug], START, END)
