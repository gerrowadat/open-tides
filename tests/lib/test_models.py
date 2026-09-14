"""Unit tests for the shared data model."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast

import aiohttp
import pytest

from pyopentides import Capabilities, Location, TideEvent, TideProvider

SESSION = cast(aiohttp.ClientSession, object())


def test_location_station() -> None:
    loc = Location(station_id="Dublin_Port")
    assert loc.station_id == "Dublin_Port"
    assert loc.lat is None


def test_location_coords() -> None:
    loc = Location(lat=58.97, lon=5.73)
    assert loc.station_id is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"station_id": "x", "lat": 1.0, "lon": 2.0},
        {"lat": 1.0},
        {"lon": 1.0},
    ],
)
def test_location_rejects_ambiguous(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Location(**kwargs)  # type: ignore[arg-type]


def test_tide_event_is_frozen() -> None:
    ev = TideEvent(time=datetime(2026, 9, 14), height_m=1.0, kind="high")
    with pytest.raises(AttributeError):
        ev.height_m = 2.0  # type: ignore[misc]


class _Minimal(TideProvider):
    slug = "minimal"
    name = "Minimal"
    attribution = "test"
    licence = "MIT"
    licence_url = "https://opensource.org/license/mit"
    datum = "LAT"
    min_refresh = timedelta(days=1)
    horizon = timedelta(days=90)
    supports_curve = True
    supports_observed = False

    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        return []


def test_abstract_without_get_events() -> None:
    class Half(TideProvider):
        slug = "half"

    with pytest.raises(TypeError):
        Half(SESSION)  # type: ignore[abstract]


async def test_capabilities_default_to_class_flags() -> None:
    caps = await _Minimal(SESSION).capabilities(Location(station_id="x"))
    assert caps == Capabilities(curve=True, observed=False)


async def test_capabilities_overridable_per_location() -> None:
    class PerStation(_Minimal):
        async def capabilities(self, loc: Location) -> Capabilities:
            return Capabilities(curve=loc.station_id != "sub", observed=False)

    p = PerStation(SESSION)
    assert (await p.capabilities(Location(station_id="ref"))).curve
    assert not (await p.capabilities(Location(station_id="sub"))).curve


async def test_optional_methods_raise_not_implemented() -> None:
    p = _Minimal(SESSION)
    loc = Location(station_id="x")
    assert await p.list_stations() is None
    with pytest.raises(NotImplementedError):
        await p.get_curve(loc, datetime(2026, 1, 1), datetime(2026, 1, 2))
    with pytest.raises(NotImplementedError):
        await p.get_observed(loc)
