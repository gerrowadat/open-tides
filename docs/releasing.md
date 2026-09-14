# Releasing

Two artefacts, two tag schemes, one repo.

| Artefact | Tag | Version lives in | Workflow |
|----------|-----|------------------|----------|
| `pyopentides` (PyPI) | `pyopentides-vX.Y.Z` | `pyproject.toml` | `release-lib.yml` |
| HA integration (HACS) | `vX.Y.Z` | `custom_components/open_tides/manifest.json` | `release-integration.yml` |

Both workflows refuse a tag that doesn't match the file version.

## Library

1. Bump `version` in `pyproject.toml` on a branch, PR, merge.
2. `git tag pyopentides-vX.Y.Z && git push origin pyopentides-vX.Y.Z`.
3. Workflow builds with `uv build` and publishes via PyPI trusted publishing.

One-time setup (manual, PyPI side): add a trusted publisher for
`gerrowadat/open-tides`, workflow `release-lib.yml`, environment `pypi`.
Create the `pypi` environment in GitHub repo settings. No token anywhere.

## Integration

1. If the integration needs a newer library, release the library first, then
   bump `requirements` in `manifest.json`.
2. Bump `version` in `manifest.json` on a branch, PR, merge.
3. `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. Workflow runs hassfest + HACS validation, zips
   `custom_components/open_tides`, creates a GitHub release with the zip.
   HACS picks it up (`zip_release: true` in `hacs.json`).

## SemVer

Breaking: entity IDs, the `events` attribute shape, config entry schema
without a migration. Anything else is minor or patch.
