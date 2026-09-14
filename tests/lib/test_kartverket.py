from __future__ import annotations

from pyopentides.models import Location

from .conftest import END, START, make_provider
from .fakesession import FakeSession

STAVANGER = Location(lat=58.974339, lon=5.730121)


async def test_heights_converted_from_cm(fake: FakeSession) -> None:
    p = make_provider("kartverket", fake)
    events = await p.get_events(STAVANGER, START, END)
    assert all(0.0 <= e.height_m <= 2.0 for e in events), "Stavanger range ~1 m"


async def test_requests_force_utc(fake: FakeSession) -> None:
    p = make_provider("kartverket", fake)
    await p.get_events(STAVANGER, START, END)
    urls = fake.urls()
    assert urls and all("tzone=0" in u for u in urls)


async def test_observed_is_latest_obs_flag(fake: FakeSession) -> None:
    p = make_provider("kartverket", fake)
    obs = await p.get_observed(STAVANGER)
    assert obs is not None
    assert obs.time.isoformat() == "2026-09-14T11:40:00+00:00"
