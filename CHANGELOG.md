# Changelog

Two artefacts, two version lines. See docs/releasing.md.

## Integration

### 0.1.2 — 2026-09-14
- Removing an entry deletes its prediction store (was orphaned).

### 0.1.1 — 2026-09-14
- Entity IDs are always `sensor.<station>_<key>`, regardless of the area naming scheme.
- Surge works with observations up to 2 days old (Marine Institute lags ~30 h).

### 0.1.0 — 2026-09-14
- Initial: config flow, Store-backed coordinator, 8 sensors, refresh service.

## pyopentides

### 0.1.0 — 2026-09-14
- Initial: contract, Marine Institute, NOAA CO-OPS, Kartverket providers.
