# open_tides

Home Assistant custom integration for tide predictions from official national
hydrographic sources, via a pluggable provider model. Read `docs/design.md` before
touching provider or coordinator code.

## What this is

- An HA custom component (`custom_components/open_tides`) distributed via HACS.
- A pure-Python client library (`pyopentides`) that HA imports. No HA
  dependency in the library. Published to PyPI.
- Providers: Marine Institute (Ireland), NOAA CO-OPS (US), Kartverket (Norway)
  at launch. Others contributed later against the same contract.

## Repo layout

```
custom_components/open_tides/   HA integration (config flow, coordinator, entities)
pyopentides/                    provider library, no HA imports
tests/lib/                      provider conformance + unit tests
tests/ha/                       integration tests using pytest-homeassistant-custom-component
scripts/record_fixtures.py      records live provider responses into tests/lib/fixtures
docs/                           user + contributor docs; docs/pyopentides.md is the PyPI readme
hacs.json, manifest.json        HACS + hassfest metadata
```

## Non-negotiables

1. **Politeness lives in the provider.** Every provider declares `min_refresh`.
   The coordinator and options flow treat it as a floor. There is no
   configuration path that lets a user poll faster than a provider allows.
2. **Restarts never cause requests.** Predictions are persisted in HA `Store`.
   On startup, load from store; fetch only if the cached window is stale or
   shorter than the horizon.
3. **Providers normalise; the core does not know provider quirks.** Times are
   timezone-aware UTC. Heights are metres. Datum is *declared*, never converted.
4. **Attribution is mandatory** and comes from the provider class, surfaced on
   every entity via `_attr_attribution`.
5. **Entity IDs and forecast attribute shape are a public contract.** Changing
   them is a breaking change and needs a major version bump.
6. **No sync I/O in HA code.** aiohttp only, via HA's shared client session.

## Ground rules

- Everything gets tested. No PR without tests for what it changes.
- Never check in secrets. No tokens, keys, or credentials in any file.
- All changes via branch + PR, squash-merged. Never commit to `main`.
- Terse. Docs describe, they don't sell. Session output: results, not narration.

## Conventions

- Python 3.12+, `from __future__ import annotations`, full type hints.
- `ruff` for lint/format, `mypy --strict` on `pyopentides`.
- Tests: `pytest`. Every provider must pass `tests/lib/test_conformance.py`
  using recorded fixtures (no live network in CI). Record with
  `scripts/record_fixtures.py`; replay is `tests/lib/fakesession.py`.
- Commit messages: conventional commits (`feat(provider-noaa): ...`).
- Provider modules are one file each: `pyopentides/providers/<slug>.py`.
- Never hard-code a dataset ID or base URL outside the provider module.
- User-Agent on every request: `open_tides/<version> (+<repo url>)`.

## Releasing

See `docs/releasing.md`. Library and integration are tagged separately.

## Commands

```
uv sync --extra dev          # Python 3.14 (HA needs it); uv installs it
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy pyopentides
```

`uv.lock` is committed; CI uses `--locked`. Tests use `tests/lib/fakesession.py`
to replay recorded fixtures — no aioresponses (it lags aiohttp).

## When adding a provider

Follow `docs/adding-a-provider.md`. Minimum: subclass `TideProvider`,
implement `list_stations` (or declare coordinate-based), `get_events`,
declare `name`, `attribution`, `licence`, `datum`, `min_refresh`, add
recorded fixtures, pass conformance tests, add a row to `docs/providers.md`.

## Things to avoid

- Don't add an "ERDDAP mode" or any transport-level abstraction. The contract
  is events and curves, not HTTP shapes.
- Don't convert between datums. Expose `datum` as an attribute instead.
- Don't add a `scan_interval` config option below the provider floor.
- Don't fetch the 20-minute curve unless the user has enabled the graph.
- Don't add telemetry.
