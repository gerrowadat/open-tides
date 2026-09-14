# Open Tides

Home Assistant integration for tide predictions from national hydrographic
sources. Providers: Marine Institute (IE), NOAA CO-OPS (US), Kartverket (NO).

Status: pre-alpha.

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
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
mypy pyopentides
```

## Licence

MIT. Tide data is under each provider's licence; see [providers](docs/providers.md).
