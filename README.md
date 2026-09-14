# Open Tides

Home Assistant integration for tide predictions from national hydrographic
sources. Providers: Marine Institute (IE), NOAA CO-OPS (US), Kartverket (NO).

Status: pre-alpha.

## Entities

Per station: tide state, next high/low time and height. Optional: predicted
height curve, observed level, surge. Predictions are cached; refresh is
floored at each provider's `min_refresh`.

## Install

HACS custom repository `gerrowadat/open-tides`, then add the integration.

## Docs

- [Providers](docs/providers.md)
- [Graphing](docs/graphing.md)
- [Adding a provider](docs/adding-a-provider.md)
- [Design](docs/design.md)

## Development

```
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
mypy pyopentides
```

## Licence

MIT. Tide data is under each provider's licence; see [providers](docs/providers.md).
