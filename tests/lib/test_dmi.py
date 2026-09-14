from __future__ import annotations

from pyopentides.models import Location

from .conftest import END, START, make_provider
from .fakesession import FakeSession

ESBJERG = Location(station_id="25149")


async def test_heights_are_metres_dvr90(fake: FakeSession) -> None:
    """cm → m; DVR90 is a land datum so lows go negative."""
    p = make_provider("dmi", fake)
    events = await p.get_events(ESBJERG, START, END)
    lows = [e.height_m for e in events if e.kind == "low"]
    highs = [e.height_m for e in events if e.kind == "high"]
    assert -1.5 < min(lows) < 0
    assert 0 < max(highs) < 1.5


async def test_curve_sorted_despite_descending_source(fake: FakeSession) -> None:
    p = make_provider("dmi", fake)
    pts = await p.get_curve(ESBJERG, START, START.replace(day=16))
    assert [x.time for x in pts] == sorted(x.time for x in pts)


async def test_gauge_same_id(fake: FakeSession) -> None:
    p = make_provider("dmi", fake)
    caps = await p.capabilities(ESBJERG)
    assert caps.observed
    obs = await p.get_observed(ESBJERG)
    assert obs is not None
    assert obs.height_m == 0.53


async def test_gauge_fallbacks(fake: FakeSession) -> None:
    """Ids differ → nearest active sealev_dvr gauge within 1 km, else none."""
    from pyopentides.models import Station

    p = make_provider("dmi", fake)
    near = Station(id="X", name="x", lat=55.4605, lon=8.4420)  # ~100 m from Esbjerg
    gauge = await p._gauge_for(near)
    assert gauge is not None and gauge.id == "25149"
    far = Station(id="Y", name="y", lat=60.1462, lon=-44.287)  # Aappilattoq, no gauge
    assert await p._gauge_for(far) is None
    assert not (await p.capabilities(Location(station_id="2991115"))).observed


async def test_requests_use_limit_and_interval(fake: FakeSession) -> None:
    p = make_provider("dmi", fake)
    await p.get_events(ESBJERG, START, END)
    urls = [u for u in fake.urls() if "tidewater/items" in u]
    assert urls
    assert all("limit=10000" in u for u in urls)
    assert all("datetime=2026-09-14T00:00:00Z/2026-09-21T00:00:00Z" in u for u in urls)
