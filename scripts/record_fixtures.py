"""Record live provider responses into tests/lib/fixtures/<slug>/.

Usage: uv run python scripts/record_fixtures.py <slug> [<slug> ...]

Hits the real APIs. Keep START/END/NOW in sync with tests/lib/conftest.py.
Prune large station lists by hand afterwards (see fixtures/README.md).
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import aiohttp
from yarl import URL

import pyopentides.provider as provider_mod
from pyopentides import ProviderError, TideProvider
from pyopentides.http import fetch_text
from pyopentides.models import Location
from pyopentides.providers import PROVIDERS

ROOT = pathlib.Path(__file__).resolve().parent.parent / "tests" / "lib" / "fixtures"
START = datetime(2026, 9, 14, tzinfo=UTC)
END = datetime(2026, 9, 21, tzinfo=UTC)
CURVE_END = datetime(2026, 9, 16, tzinfo=UTC)
NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)

Call = tuple[str, Callable[[TideProvider], Awaitable[Any]]]

# Per provider: the calls to record. A known-good location, a bad one, and
# whatever else the provider's own tests need.
CALLS: dict[str, list[Call]] = {
    "marine_ie": [
        ("stations", lambda p: p.list_stations()),
        ("caps", lambda p: p.capabilities(Location(station_id="Dublin_Port"))),
        (
            "events",
            lambda p: p.get_events(Location(station_id="Dublin_Port"), START, END),
        ),
        (
            "curve",
            lambda p: p.get_curve(Location(station_id="Dublin_Port"), START, CURVE_END),
        ),
        ("observed", lambda p: p.get_observed(Location(station_id="Dublin_Port"))),
        (
            "caps modelled",
            lambda p: p.capabilities(Location(station_id="Wicklow_MODELLED")),
        ),
        (
            "events bad",
            lambda p: p.get_events(Location(station_id="Nowhere"), START, END),
        ),
    ],
    "noaa_coops": [
        ("stations", lambda p: p.list_stations()),
        ("caps sf", lambda p: p.capabilities(Location(station_id="9414290"))),
        ("caps sub", lambda p: p.capabilities(Location(station_id="1610367"))),
        (
            "events sf",
            lambda p: p.get_events(Location(station_id="9414290"), START, END),
        ),
        (
            "events sub",
            lambda p: p.get_events(Location(station_id="1610367"), START, END),
        ),
        (
            "curve sf",
            lambda p: p.get_curve(Location(station_id="9414290"), START, CURVE_END),
        ),
        ("observed sf", lambda p: p.get_observed(Location(station_id="9414290"))),
        (
            "events bad",
            lambda p: p.get_events(Location(station_id="0000000"), START, END),
        ),
    ],
    "dmi": [
        ("stations", lambda p: p.list_stations()),
        ("caps", lambda p: p.capabilities(Location(station_id="25149"))),
        ("events", lambda p: p.get_events(Location(station_id="25149"), START, END)),
        (
            "curve",
            lambda p: p.get_curve(Location(station_id="25149"), START, CURVE_END),
        ),
        ("observed", lambda p: p.get_observed(Location(station_id="25149"))),
        ("events bad", lambda p: p.get_events(Location(station_id="0"), START, END)),
    ],
    "kartverket": [
        (
            "events",
            lambda p: p.get_events(Location(lat=58.974339, lon=5.730121), START, END),
        ),
        (
            "curve",
            lambda p: p.get_curve(
                Location(lat=58.974339, lon=5.730121), START, CURVE_END
            ),
        ),
        ("observed", lambda p: p.get_observed(Location(lat=58.974339, lon=5.730121))),
        (
            "events bad",
            lambda p: p.get_events(Location(lat=53.3, lon=-6.2), START, END),
        ),
    ],
}


async def record(slug: str) -> None:
    out = ROOT / slug
    out.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []

    async def recording_fetch(
        session: aiohttp.ClientSession,
        url: str,
        *,
        params: dict[str, str] | None = None,
        user_agent: str,
        not_found_is_station: bool = False,
    ) -> str:
        full = str(URL(url).with_query(dict(params))) if params else url
        name = f"r{len(manifest)}.txt"
        try:
            body = await fetch_text(
                session,
                url,
                params=params,
                user_agent=user_agent,
                not_found_is_station=not_found_is_station,
            )
            status = 200
        except ProviderError as err:
            status = getattr(err, "status", None) or 404
            body = getattr(err, "body", "") or ""
            manifest.append({"url": full, "status": status, "body": name})
            (out / name).write_text(body)
            raise
        manifest.append({"url": full, "status": status, "body": name})
        (out / name).write_text(body)
        return body

    provider_mod.fetch_text = recording_fetch  # type: ignore[assignment]
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as session:
        provider = PROVIDERS[slug](session, version="record")
        provider._now = staticmethod(lambda: NOW)  # type: ignore[method-assign]
        for label, fn in CALLS[slug]:
            try:
                result = await fn(provider)
                n = len(result) if hasattr(result, "__len__") else result
                print(f"[{slug}] {label}: ok ({n})")
            except ProviderError as err:
                print(f"[{slug}] {label}: {type(err).__name__}: {err}")
    (out / "requests.json").write_text(json.dumps(manifest, indent=1) + "\n")


if __name__ == "__main__":
    for s in sys.argv[1:] or sorted(CALLS):
        asyncio.run(record(s))
