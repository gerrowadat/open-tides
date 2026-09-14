# Providers

<!-- PLACEHOLDER: expand each section as the provider is implemented. -->

Every provider is one module at `pyopentides/providers/<slug>.py` and must
pass `tests/lib/test_conformance.py`. This page is the user-facing summary;
the contract itself is in [design.md](design.md).

## Summary

| Slug         | Provider / Source                 | Region  | Stations | Curve | Observed | Datum | Licence | min_refresh | Status  |
|--------------|-----------------------------------|---------|----------|-------|----------|-------|---------|-------------|---------|
| `marine_ie`  | Marine Institute (ERDDAP)         | Ireland | list     | yes   | yes      | LAT   | TBD     | 7 days      | planned |
| `noaa_coops` | NOAA CO-OPS API                   | US      | list     | yes   | yes      | MLLW  | TBD     | 1 day       | planned |
| `kartverket` | Kartverket *Se havnivå* API       | Norway  | coords   | yes   | yes      | CD    | TBD     | 1 day       | planned |

Datum is declared by the provider and exposed as an entity attribute. It is
never converted — heights from different providers are not comparable.

## marine_ie — Marine Institute (Ireland)

<!-- TODO: dataset ID(s), base URL, attribution string, licence, quirks. -->

- Source: Marine Institute ERDDAP
- Dataset ID: TBD (configurable via class attribute; has rotated before)
- Attribution: TBD
- Licence: TBD
- Notes: TBD

## noaa_coops — NOAA CO-OPS (United States)

<!-- TODO: base URL, product/datum/interval parameters, attribution, licence, quirks. -->

- Source: NOAA CO-OPS Data API
- Attribution: TBD
- Licence: TBD (US Government work, public domain — confirm)
- Notes: TBD

## kartverket — Kartverket (Norway)

<!-- TODO: base URL, coordinate query parameters, attribution, licence, quirks. -->

- Source: Kartverket *Se havnivå* API
- Coordinate-based: no station list; queried by lat/lon
- Attribution: TBD
- Licence: TBD
- Notes: TBD

## Adding a provider

See [adding-a-provider.md](adding-a-provider.md).
