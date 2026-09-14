# Open Tides

Home Assistant integration for tide predictions from national hydrographic
sources, plus the Python library it's built on.

| Provider | Region | Datum | Curve | Observed | Licence |
|----------|--------|-------|-------|----------|---------|
| Marine Institute | Ireland | LAT | yes | yes | CC BY 4.0 |
| NOAA CO-OPS | United States | MLLW | harmonic stations | yes | public domain |
| Kartverket | Norway | CD | yes | yes | CC BY 4.0 |
| DMI | Denmark, Greenland, Faroe Islands | DVR90 | yes | yes | CC BY 4.0 |

Status: alpha. Tested against HA 2026.9 in CI; not yet exercised on a live install.

## Install

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gerrowadat&repository=open-tides&category=integration)
[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=open_tides)

HACS → custom repository `gerrowadat/open-tides` (integration), then add the
integration. Pick a provider, then a station (or a coordinate for Kartverket;
defaults to your home).

## Entities

One device per station. `<name>` is the station name.

| Entity | State |
|--------|-------|
| `sensor.<name>_tide` | `rising` / `falling`. Attributes: `events` (next 48 h), `curve` (if enabled), `datum`, `provider`, `station`, `attribution`, `licence`, `licence_url` |
| `sensor.<name>_next_high`, `_next_low` | timestamp |
| `sensor.<name>_next_high_height`, `_next_low_height` | metres |
| `sensor.<name>_predicted_height` | metres, now (curve option) |
| `sensor.<name>_observed_height` | metres, latest gauge reading (observed option) |
| `sensor.<name>_surge` | observed − predicted, metres (observed option) |

Heights are relative to the provider's datum. Not comparable across providers.

## Options

- **Refresh interval** — floored at the provider's minimum (7 d Marine
  Institute and DMI, 1 d NOAA and Kartverket). Predictions don't change; there is
  nothing to gain by polling faster.
- **Height curve** — fetch the predicted curve. Enables `predicted_height`
  and the `curve` attribute.
- **Observed level** — poll the gauge. Enables `observed_height` and
  `surge`. Not available at modelled or subordinate stations.

Predictions are cached on disk. Restarts never cause a request.

## Service

`open_tides.refresh` — refetch predictions. Ignored, with a warning, if the
provider's minimum interval hasn't elapsed. Optional `entry_id` list.

## Docs

- [Providers](docs/providers.md) — endpoints, datums, licences, quirks
- [Graphing](docs/graphing.md) — TideWise and ApexCharts configs
- [pyopentides](docs/pyopentides.md) — the library, with usage
- [API landscape](docs/api-landscape.md) — how hydrographic offices publish tides
- [The science bit](docs/science.md)
- [Adding a provider](docs/adding-a-provider.md)
- [Design](docs/design.md)
- [Releasing](docs/releasing.md)

## Development

```
uv sync --extra dev
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy pyopentides
```

## Licence

MIT. Tide data is under each provider's licence; attribution is on every
entity.
