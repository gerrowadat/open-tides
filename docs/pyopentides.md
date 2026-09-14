# pyopentides

Tide predictions from official national hydrographic sources. One contract,
many providers. Pure Python, `aiohttp`, no Home Assistant dependency.

Providers: Marine Institute (Ireland), NOAA CO-OPS (United States),
Kartverket (Norway), DMI (Denmark, Greenland, Faroe Islands). Details, datums and licences:
[providers.md](https://github.com/gerrowadat/open-tides/blob/main/docs/providers.md).

## Install

```
pip install pyopentides
```

Python ≥ 3.12.

## Usage

```python
import asyncio
from datetime import UTC, datetime, timedelta

import aiohttp

from pyopentides import Location
from pyopentides.providers import PROVIDERS


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        provider = PROVIDERS["marine_ie"](session, version="my-app/1.0")

        stations = await provider.list_stations()          # None if coordinate_based
        dublin = next(s for s in stations if s.id == "Dublin_Port")
        loc = Location(station_id=dublin.id)

        now = datetime.now(UTC)
        events = await provider.get_events(loc, now, now + timedelta(days=7))
        for e in events:
            print(e.time.isoformat(), e.kind, f"{e.height_m:.2f} m {provider.datum}")

        caps = await provider.capabilities(loc)
        if caps.curve:
            curve = await provider.get_curve(loc, now, now + timedelta(hours=48))
        if caps.observed:
            obs = await provider.get_observed(loc)

        print(provider.attribution)


asyncio.run(main())
```

Coordinate-based provider:

```python
provider = PROVIDERS["kartverket"](session)
loc = Location(lat=58.974, lon=5.730)          # Stavanger
events = await provider.get_events(loc, start, end)
```

## What you get back

All times are timezone-aware UTC. All heights are metres, relative to the
provider's declared `datum`. Never converted.

| Type | Fields |
|------|--------|
| `Station` | `id`, `name`, `lat`, `lon` |
| `Location` | exactly one of `station_id` or (`lat`, `lon`) |
| `TideEvent` | `time`, `height_m`, `kind` (`"high"` / `"low"`) |
| `Point` | `time`, `height_m` |
| `Observation` | `time`, `height_m` |
| `Capabilities` | `curve`, `observed` — per location |

Guarantees on `get_events` and `get_curve`: sorted ascending, no duplicate
times, nothing outside `[start, end]`. Events alternate high/low.

## Provider attributes

| Attribute | Meaning |
|-----------|---------|
| `slug`, `name` | identity; slugs are permanent |
| `attribution`, `licence`, `licence_url` | show `attribution` wherever the data is shown; CC BY requires it |
| `datum` | `"LAT"`, `"MLLW"`, `"CD"`, … |
| `coordinate_based` | `True`: no station list, query by lat/lon |
| `min_refresh` | **floor** on how often to call `get_events`; days, not minutes |
| `horizon` | how far ahead one fetch covers (90 d); fetch that, then stop |
| `supports_curve`, `supports_observed` | provider can *ever*; check `capabilities(loc)` for a given location |
| `observed_min_refresh` | floor for `get_observed` |

## Errors

All `ProviderError` subclasses. Nothing from `aiohttp` escapes.

| Exception | When |
|-----------|------|
| `StationNotFound` | unknown station id, or a coordinate the provider doesn't cover |
| `ProviderRateLimited` | HTTP 429 |
| `ProviderUnavailable` | anything else: down, timeout, unparseable. Has `.status` and `.body` for HTTP errors |

## Politeness

The library does not rate-limit or cache. You must:

- Call `get_events` at most once per `min_refresh` per location, and fetch
  `horizon` ahead so that's enough.
- Persist the result. Predictions don't change; there is no reason to
  re-fetch on restart.
- Pass a `version` string; it goes into the `User-Agent`
  (`open_tides/<version> (+https://github.com/gerrowadat/open-tides)`).

These are shared public services run by hydrographic offices. See
[api-landscape.md](https://github.com/gerrowadat/open-tides/blob/main/docs/api-landscape.md)
for what each one asks of clients.

## Adding a provider

[adding-a-provider.md](https://github.com/gerrowadat/open-tides/blob/main/docs/adding-a-provider.md).

## Licence

MIT. Data is under each provider's own licence.
