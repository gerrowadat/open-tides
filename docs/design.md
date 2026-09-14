# open_tides — design

## Goal

Tide state, next high/low, and an optional height curve in Home Assistant,
sourced from official national predictions, without hammering the agencies
that publish them. Generic from day one: one integration, many providers.

## Why not the existing options

- NOAA Tides (core): US only, YAML only.
- World Tides (core): paid per-request API.
- UKHO integrations: licence forbids caching; polling is the only mode.
- Norwegian / Galician / NOAA-rewrite custom components: one country each,
  no shared contract.

Every agency has a bespoke API. What they share is the *output*: a list of
high/low events, and sometimes a height-vs-time curve. That is the
abstraction.

## Provider contract

```python
class TideProvider(ABC):
    # Identity
    slug: str                 # "marine_ie", "noaa_coops", "kartverket"
    name: str                 # human-readable
    attribution: str          # shown on every entity
    licence: str              # e.g. "CC-BY-4.0"
    datum: str                # "LAT", "MLLW", "CD", ...
    coordinate_based: bool    # True = no station list, query by lat/long

    # Politeness
    min_refresh: timedelta    # hard floor for polling; coordinator enforces
    horizon: timedelta        # how far ahead one fetch retrieves (e.g. 90 days)
    supports_curve: bool
    supports_observed: bool
    observed_min_refresh: timedelta | None  # required if supports_observed; separate floor (e.g. 10 min)

    async def list_stations(self) -> list[Station] | None: ...
    async def get_events(self, loc: Location, start: datetime, end: datetime) -> list[TideEvent]: ...
    async def get_curve(self, loc: Location, start: datetime, end: datetime) -> list[Point]: ...      # optional
    async def get_observed(self, loc: Location) -> Observation | None: ...                           # optional
```

### Data model

```python
@dataclass(frozen=True)
class Station:
    id: str; name: str; lat: float; lon: float

@dataclass(frozen=True)
class Location:            # either a station id or a coordinate
    station_id: str | None
    lat: float | None
    lon: float | None

@dataclass(frozen=True)
class TideEvent:
    time: datetime         # tz-aware UTC
    height_m: float
    kind: Literal["high", "low"]

@dataclass(frozen=True)
class Point:
    time: datetime; height_m: float

@dataclass(frozen=True)
class Observation:
    time: datetime; height_m: float
```

### Normalisation rules (provider responsibility)

- Convert to UTC and metres inside the provider.
- Never convert datum. Declare it. The entity exposes it as an attribute.
- Sort events ascending; drop duplicates; reject any event outside
  `[start, end]`.
- Raise `ProviderError` subclasses (`ProviderUnavailable`, `ProviderRateLimited`,
  `StationNotFound`) — never leak aiohttp exceptions.

## Launch providers

| Provider        | Source                         | Stations | Curve | Observed | Datum | min_refresh |
|-----------------|--------------------------------|----------|-------|----------|-------|-------------|
| marine_ie       | Marine Institute ERDDAP        | list     | yes   | yes      | LAT   | 7 days      |
| noaa_coops      | NOAA CO-OPS API                | list     | yes   | yes      | MLLW  | 1 day       |
| kartverket      | Kartverket sehavniva API       | coords   | yes   | yes      | CD    | 1 day       |

These three were chosen because they cover the distinct shapes: station +
events (all), curve + constituents (NOAA), and coordinate-based with no
station list (Kartverket). A fourth provider should not need a new concept.

Notes per provider live in `docs/providers.md`. Keep dataset IDs and base
URLs configurable via class attributes — Marine Institute has already
rotated dataset IDs once.

## Politeness

- `min_refresh` is a floor. Options flow offers intervals ≥ floor only.
- Coordinator fetches `horizon` ahead in one request, so a single fetch per
  refresh period is enough and a missed refresh degrades gracefully.
- Predictions persisted in `homeassistant.helpers.storage.Store`, keyed by
  config entry. Startup reads the store first; fetches only if
  `cached_end - now < horizon / 2` or the store is empty.
- Random jitter (up to 10% of interval) applied to the refresh schedule.
- `open_tides.refresh` service exists for cache recovery but is subject to
  the same floor. Calling it early logs a warning and does nothing.
- Every request carries `User-Agent: open_tides/<version> (+<repo url>)`.
- Curve is fetched only when the user enables it, and only for the next
  48 h.
- Observed level (if enabled) is the one thing that polls more often —
  provider declares `observed_min_refresh` separately (e.g. 10 min).

## Config flow

1. Choose provider.
2. If `coordinate_based`: use HA home lat/long by default, allow override.
   Else: station dropdown from `list_stations()` (cached in the flow).
3. Options: refresh interval (≥ floor), enable curve, enable observed.

Unique ID: `{provider_slug}:{station_id or f"{lat:.3f},{lon:.3f}"}`.

## Entities

Per config entry, one device. Entities:

| Entity                          | Type            | State                    |
|---------------------------------|-----------------|--------------------------|
| `sensor.<name>_tide`            | sensor (enum)   | `rising` / `falling`     |
| `sensor.<name>_next_high`       | sensor (timestamp) | ISO time              |
| `sensor.<name>_next_low`        | sensor (timestamp) | ISO time              |
| `sensor.<name>_next_high_height`| sensor (m)      | float                    |
| `sensor.<name>_next_low_height` | sensor (m)      | float                    |
| `sensor.<name>_predicted_height`| sensor (m)      | interpolated now (curve on) |
| `sensor.<name>_observed_height` | sensor (m)      | latest gauge (observed on) |
| `sensor.<name>_surge`           | sensor (m)      | observed − predicted     |

Attributes on `sensor.<name>_tide` (the public contract):

```yaml
datum: LAT
provider: marine_ie
station: Dublin Port
attribution: ...
events:            # next 48 h of highs/lows
  - time: 2026-09-14T18:12:00+00:00
    height: 4.12
    type: high
curve:             # only when enabled; next 48 h, 20-min step
  - [2026-09-14T15:00:00+00:00, 2.31]
```

The `events` shape should match what TideWise's generic-sensor mode expects;
verify against their current docs before release and adjust here, not there.

## Graphing

No card shipped in v1. Document an ApexCharts config using `data_generator`
on the `curve` attribute, and a TideWise config pointing at
`sensor.<name>_tide`.

## Testing

- `tests/lib/test_conformance.py` runs the same assertions against every
  registered provider using recorded HTTP fixtures (`aioresponses`).
  Assertions: events sorted, UTC, metres, within range, alternating kinds,
  attribution non-empty, `min_refresh` ≥ 1 h.
- Providers may add their own unit tests for parsing edge cases.
- HA tests: config flow happy path, store round-trip, floor enforcement,
  entity state derivation from a fixed event list.

## Versioning and compatibility

- SemVer. Entity IDs and the `events` attribute shape are covered by it.
- `pyopentides` versioned independently; the integration pins a compatible
  range in `manifest.json`.

## Contributing a provider

See `docs/adding-a-provider.md`. Short version: one module, one fixture set,
pass conformance, one table row in `docs/providers.md`, attribution and
licence declared. PRs that add transport-level abstractions or datum
conversion will be declined.

## Out of scope for v1

- Offline harmonic prediction from constituents (leave a subclass slot;
  it fits the contract cleanly).
- A custom Lovelace card.
- Datum conversion.
- Currents, water temperature, or anything that isn't sea level.
