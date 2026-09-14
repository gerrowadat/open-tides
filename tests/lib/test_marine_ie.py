from __future__ import annotations

import aiohttp
from aioresponses import aioresponses

from pyopentides.models import Location

from .conftest import END, START, make_provider


async def test_events_are_lat_not_odm(
    session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    """HighLow is OD Malin; provider adds the LAT offset. LAT lows are ≥ 0."""
    p = make_provider("marine_ie", session, mocked)
    events = await p.get_events(Location(station_id="Dublin_Port"), START, END)
    lows = [e.height_m for e in events if e.kind == "low"]
    highs = [e.height_m for e in events if e.kind == "high"]
    assert min(lows) >= 0.0
    assert 3.0 < max(highs) < 5.0  # Dublin springs ~4.1 m LAT


async def test_modelled_station_has_no_observed(
    session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    p = make_provider("marine_ie", session, mocked)
    caps = await p.capabilities(Location(station_id="Wicklow_MODELLED"))
    assert caps.curve and not caps.observed


async def test_gauge_matched_by_distance(
    session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    p = make_provider("marine_ie", session, mocked)
    caps = await p.capabilities(Location(station_id="Dublin_Port"))
    assert caps.observed
    obs = await p.get_observed(Location(station_id="Dublin_Port"))
    assert obs is not None
