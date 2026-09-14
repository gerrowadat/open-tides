# Open Tides

Home Assistant integration for tide predictions from national hydrographic
sources. Providers: Marine Institute (IE), NOAA CO-OPS (US), Kartverket (NO).

Status: pre-alpha. Providers and integration implemented; no release yet. Tested against HA 2026.9.

## Entities

Per station: tide state, next high/low time and height. Optional: predicted
height curve, observed level, surge. Predictions are cached; refresh is
floored at each provider's `min_refresh`.

## Install

Not yet. There is no release; these buttons don't work until there is.

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gerrowadat&repository=open-tides&category=integration)
[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=open_tides)

Once released: HACS custom repository `gerrowadat/open-tides`, then add the
integration.

## Docs

- [Providers](docs/providers.md)
- [Graphing](docs/graphing.md)
- [API landscape](docs/api-landscape.md)
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

MIT. Tide data is under each provider's licence; see [providers](docs/providers.md).
