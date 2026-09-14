# Adding a provider

<!-- PLACEHOLDER: flesh out once the first provider and the conformance
     test exist, so the examples here are real code, not sketches. -->

Read [design.md](design.md) first — particularly the provider contract,
the normalisation rules, and the politeness section. This page is the
checklist.

## Checklist

1. **One module**: `pyopentides/providers/<slug>.py`. No HA imports.
2. **Subclass `TideProvider`** and declare:
   - `slug`, `name`, `attribution`, `licence`, `licence_url`, `datum`
   - `coordinate_based`
   - `min_refresh` (≥ 1 h; conformance enforces this), `horizon`
   - `supports_curve`, `supports_observed`
   - `observed_min_refresh` if `supports_observed`
3. **Implement** `get_events`, and either `list_stations` or set
   `coordinate_based = True`. `get_curve` and `get_observed` are optional.
4. **Normalise inside the provider**: UTC, metres, sorted, de-duplicated,
   nothing outside `[start, end]`. Declare the datum; never convert it.
5. **Errors**: raise `ProviderUnavailable`, `ProviderRateLimited`, or
   `StationNotFound`. Never leak aiohttp exceptions.
6. **Config, not constants**: dataset IDs and base URLs are class
   attributes on the provider. They must not appear anywhere else.
7. **User-Agent** on every request: `open_tides/<version> (+<repo url>)`.
8. **Fixtures**: record real responses into `tests/lib/fixtures/<slug>/`
   and use `aioresponses`. No live network in CI.
9. **Conformance**: register the provider so `tests/lib/test_conformance.py`
   picks it up, and make it pass.
10. **Docs**: add a row and a section to [providers.md](providers.md).

## What will be declined

- Transport-level abstractions ("ERDDAP mode", generic REST helpers that
  leak HTTP shapes into the core).
- Datum conversion of any kind.
- Any path that lets a user poll faster than `min_refresh`.

## Skeleton

<!-- TODO: replace with a real minimal provider once the base class lands. -->

```python
from __future__ import annotations

from datetime import datetime, timedelta

from pyopentides.provider import TideProvider
from pyopentides.models import Location, Station, TideEvent


class ExampleProvider(TideProvider):
    slug = "example"
    name = "Example Hydrographic Office"
    attribution = "Tide predictions © Example Hydrographic Office"
    licence = "CC-BY-4.0"
    licence_url = "https://creativecommons.org/licenses/by/4.0/"
    datum = "LAT"
    coordinate_based = False

    min_refresh = timedelta(days=1)
    horizon = timedelta(days=90)
    supports_curve = False
    supports_observed = False

    base_url = "https://example.invalid/api"

    async def list_stations(self) -> list[Station] | None:
        raise NotImplementedError

    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        raise NotImplementedError
```

## Recording fixtures

<!-- TODO: document the recording helper once it exists. -->
