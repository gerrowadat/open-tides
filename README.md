# Open Tides

Tide predictions in Home Assistant from official national hydrographic
sources — Marine Institute (Ireland), NOAA CO-OPS (US), Kartverket (Norway),
with more contributed against the same provider contract.

**Status: pre-alpha. Nothing works yet.**

## What you get

Per station (or coordinate): tide state (rising/falling), next high/low with
times and heights, and optionally a predicted height curve and observed
gauge level. Predictions are cached locally and refreshed no more often than
each provider allows — restarts never cause requests.

## Install

Via HACS as a custom repository (`gerrowadat/open-tides`), then add the
integration from *Settings → Devices & services*.

## Docs

- [Providers](docs/providers.md)
- [Graphing the curve](docs/graphing.md)
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

MIT. Tide data is subject to each provider's own licence; see
[docs/providers.md](docs/providers.md).
