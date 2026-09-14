from __future__ import annotations

from pyopentides.models import Location

from .conftest import END, START, make_provider
from .fakesession import FakeSession


async def test_subordinate_station_has_events_but_no_curve(fake: FakeSession) -> None:
    p = make_provider("noaa_coops", fake)
    sub = Location(station_id="1610367")
    caps = await p.capabilities(sub)
    assert not caps.curve and not caps.observed
    events = await p.get_events(sub, START, END)
    assert len(events) >= 20


async def test_harmonic_station_capabilities(fake: FakeSession) -> None:
    p = make_provider("noaa_coops", fake)
    caps = await p.capabilities(Location(station_id="9414290"))
    assert caps.curve and caps.observed


async def test_requests_carry_application_and_gmt(fake: FakeSession) -> None:
    p = make_provider("noaa_coops", fake)
    await p.get_events(Location(station_id="9414290"), START, END)
    urls = fake.urls()
    data = [u for u in urls if "datagetter" in u]
    assert data and all("application=open_tides" in u for u in data)
    assert all("time_zone=gmt" in u and "units=metric" in u for u in data)
