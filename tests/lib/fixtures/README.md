# Recorded fixtures

One directory per provider slug. `requests.json` lists `{url, status, body}`
exactly as the provider requested them; bodies are the raw responses. Replayed
with `aioresponses`; no network in tests.

Recorded 2026-09-14 for the window 2026-09-14T00:00Z → 2026-09-21T00:00Z
(curve to 2026-09-16), "now" frozen at 2026-09-14T12:00Z. NOAA station lists
are pruned to four stations.

To re-record: run the provider live with `pyopentides.provider.fetch_text`
wrapped to capture URL + body, then prune. Keep the window and NOW the same
or update `tests/lib/conftest.py`.
