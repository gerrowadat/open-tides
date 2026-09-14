# Adding a provider

Read [design.md](design.md) first: the contract, normalisation rules,
politeness. This page is the procedure. `pyopentides/providers/kartverket.py`
is the smallest real example; `marine_ie.py` the most involved.

## Checklist

1. **One module**: `pyopentides/providers/<slug>.py`. No HA imports. Slug is
   permanent — it's in users' config entries.
2. **Research first.** Add a section to [providers.md](providers.md): base
   URL, endpoints, response shape, datum, units, limits, licence, attribution
   wording, quirks. If the licence forbids caching, stop; it can't be a
   provider (see UKHO in [api-landscape.md](api-landscape.md)).
3. **Subclass `TideProvider`** and declare `slug`, `name`, `attribution`,
   `licence`, `licence_url`, `datum`, `coordinate_based`, `min_refresh`
   (≥ 1 h), `horizon` (≥ 7 d), `supports_curve`, `supports_observed`,
   `observed_min_refresh` (if observed).
4. **Implement** `get_events`, and `list_stations` unless
   `coordinate_based`. Optional: `get_curve`, `get_observed`, and
   `capabilities(loc)` when it varies by station.
5. **Normalise**: use `normalise_events` / `normalise_points`. Convert to
   metres and UTC yourself. Declare the datum; never convert it.
6. **Errors**: `StationNotFound`, `ProviderRateLimited`, `ProviderUnavailable`.
   `self._get()` maps transport and HTTP errors; you map provider-specific
   ones (a 400 with a JSON error, an XML `<nodata>`).
7. **Constants**: base URLs and dataset ids are `ClassVar` attributes on
   the class. Nowhere else.
8. **Register** in `pyopentides/providers/__init__.py`.
9. **Fixtures**: add your calls to `scripts/record_fixtures.py`, run it,
   prune anything large, commit `tests/lib/fixtures/<slug>/`.
10. **Tests**: add your location to `LOCATIONS` and `BAD` in
    `tests/lib/test_conformance.py`; add `tests/lib/test_<slug>.py` for the
    quirks you found in step 2 (units, timezone, offsets, per-station
    capabilities).
11. **Docs**: providers.md summary row → `done`.

## Skeleton

```python
"""Example Hydrographic Office. See docs/providers.md#example."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from pyopentides.exceptions import ProviderUnavailable, StationNotFound
from pyopentides.models import Location, Station, TideEvent
from pyopentides.normalise import ensure_utc, normalise_events
from pyopentides.provider import TideProvider


class ExampleProvider(TideProvider):
    slug = "example"
    name = "Example Hydrographic Office"
    attribution = "Tide predictions © Example Hydrographic Office (CC BY 4.0)"
    licence = "CC-BY-4.0"
    licence_url = "https://creativecommons.org/licenses/by/4.0/"
    datum = "LAT"
    coordinate_based = False

    min_refresh = timedelta(days=1)
    horizon = timedelta(days=90)
    supports_curve = False
    supports_observed = False

    base_url: ClassVar[str] = "https://example.invalid/api"

    async def list_stations(self) -> list[Station] | None:
        text = await self._get(f"{self.base_url}/stations")
        return [Station(id=s["id"], name=s["name"], lat=s["lat"], lon=s["lon"])
                for s in json.loads(text)]

    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        if loc.station_id is None:
            raise StationNotFound("example is station-based")
        text = await self._get(
            f"{self.base_url}/tides",
            {"station": loc.station_id,
             "from": ensure_utc(start).isoformat(),
             "to": ensure_utc(end).isoformat()},
            not_found_is_station=True,
        )
        events = [
            TideEvent(
                time=datetime.fromisoformat(r["t"]).astimezone(UTC),
                height_m=float(r["h"]),
                kind="high" if r["type"] == "H" else "low",
            )
            for r in json.loads(text)
        ]
        return normalise_events(events, start, end)
```

## Fixtures and replay

Tests never touch the network. `scripts/record_fixtures.py` runs the
provider live with `pyopentides.provider.fetch_text` wrapped, and writes
`requests.json` (`url`, `status`, `body` file) plus the raw bodies.
`tests/lib/fakesession.py` replays them by exact URL. `make_provider(slug,
fake)` in `tests/lib/conftest.py` wires it up and freezes `_now()`.

Consequences:

- Build URLs deterministically from the inputs. Anything derived from wall
  clock must go through `self._now()`.
- Record the failure cases too (bad station, out-of-coverage coordinate).
- Keep fixtures small. Prune station lists to the stations tests use.

## Things that will be declined

- Transport abstractions ("ERDDAP mode", generic REST helpers).
- Datum conversion.
- Anything that polls faster than the provider allows.
- A provider whose licence forbids caching.
