# Providers

Facts as of 2026-09-14. Each provider is one module at
`pyopentides/providers/<slug>.py` and must pass `tests/lib/test_conformance.py`.
Contract: [design.md](design.md). Landscape: [api-landscape.md](api-landscape.md).

## Summary

| Slug         | Source                      | Region | Stations | Curve | Observed | Datum      | Licence   | min_refresh | Status  |
|--------------|-----------------------------|--------|----------|-------|----------|------------|-----------|-------------|---------|
| `marine_ie`  | Marine Institute ERDDAP     | IE     | list     | 5 min | yes      | LAT (+ODM) | CC BY 4.0 | 7 d         | done    |
| `noaa_coops` | NOAA CO-OPS Data API        | US     | list     | 6 min | yes      | MLLW       | public domain | 1 d     | planned |
| `kartverket` | Kartverket *Se havnivå* API | NO     | coords   | 10 min| yes      | CD         | CC BY 4.0 | 1 d         | done    |

Datum is declared, never converted. Heights from different providers are not
comparable.

---

## marine_ie — Marine Institute (Ireland)

**Base:** `https://erddap.marine.ie/erddap/tabledap/`
**Licence:** CC BY 4.0 (per-dataset `license` attribute). <https://creativecommons.org/licenses/by/4.0/>
**Attribution:** "Tide predictions © Marine Institute, Ireland (CC BY 4.0)".
**Contact:** datarequests@marine.ie.

### Datasets

| ID | What | Datum | Step |
|----|------|-------|------|
| `imiTidePrediction` | Predicted level. `Water_Level` (LAT), `Water_Level_ODM` (OD Malin) | LAT, ODM | 5 min |
| `IMI_TidePrediction_HighLow` | High/low events. `tide_time_category` = `HIGH`/`LOW`, `Water_Level_ODMalin` | **ODM only** | event |
| `IrishNationalTideGaugeNetwork` | Observed. `Water_Level_LAT`, `Water_Level_OD_Malin`, `QC_Flag` | LAT, ODM | 1–5 min |
| `imiSurgePrediction` | 3-day tide + surge forecast | ODM / MSL | — |
| `IMI-TidePrediction` | Legacy, "to be replaced". Don't use. | | |

Dataset IDs have rotated before. Keep them as class attributes.

### Notes

- 38 stations. IDs like `Dublin_Port`. Suffix `_MODELLED` = from the
  hydrodynamic model, no gauge, no observed data.
- HighLow is ODM only. To emit LAT events, either use HighLow and add the
  station's LAT–ODM offset (derivable from `imiTidePrediction`, which carries
  both), or detect extrema from the 5-min series. Decide in the provider,
  document it.
- Coverage: ~2 years ahead (`time_coverage_end` 2029-01-01 at time of writing).
- Station list: `imiTidePrediction.csv?stationID,longitude,latitude&distinct()`.
- Query: `imiTidePrediction.csv?time,stationID,Water_Level&stationID="Dublin_Port"&time>=…&time<=…`.
- No published rate limit. ERDDAP is a shared research server; one request per
  week per station at a 90-day horizon is the right order of magnitude.
- Legal: <https://erddap.marine.ie/erddap/legal.html>.
- Observed gauge network: <https://www.irishtides.ie/>.

---

## noaa_coops — NOAA CO-OPS (United States)

**Base:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
**Metadata:** `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/`
**Licence:** US Government work, public domain. NOAA requests attribution. <https://www.noaa.gov/information-technology/disclaimer>
**Attribution:** "Tide predictions courtesy of NOAA CO-OPS".

### Endpoints

| Need | Request |
|------|---------|
| Stations | `mdapi …/stations.json?type=tidepredictions&units=metric` |
| Events | `product=predictions&interval=hilo&datum=MLLW&units=metric&time_zone=gmt&format=json` |
| Curve | `product=predictions&interval=6` (harmonic stations only) |
| Observed | `product=water_level&date=latest&datum=MLLW&units=metric` |
| Datums | `mdapi …/stations/{id}/datums.json` |

### Response shape

- Predictions hilo: `{"predictions":[{"t":"2026-09-14 05:12","v":"1.234","type":"H"}]}`.
  `type` ∈ `H`, `L` (also `HH`/`LL` in some products). `t` has no zone; use
  `time_zone=gmt` and attach UTC.
- Water level: `{"data":[{"t":…,"v":…,"s":…,"f":…,"q":"p"|"v"}]}`.

### Limits

| Product | Max span |
|---------|----------|
| predictions hilo | 1 year (docs vary; 10 years in some) |
| predictions 6-min | 1 year |
| water_level 6-min | 31 days |

### Notes

- Station types: harmonic (`R`) — any interval; subordinate (`S`) — hilo
  only, derived by time/height offsets from a reference station. The provider
  must set `supports_curve` per station, not per provider.
- Always pass `application=open_tides`. NOAA asks for it and uses it in logs.
- Datum: MLLW is standard for US charts. Some Great Lakes stations use IGLD;
  `STND` = station datum. Provider declares MLLW and should refuse stations
  that don't offer it.
- No hard rate limit published. NOAA: "throttling applies to heavy loads";
  add sleeps between requests. One request/day/station is far under any
  threshold.
- Disclaimer: <https://tidesandcurrents.noaa.gov/disclaimers.html>.
- API docs: <https://api.tidesandcurrents.noaa.gov/api/prod/>.

---

## kartverket — Kartverket / Norwegian Hydrographic Service (Norway)

**Base:** `https://vannstand.kartverket.no/tideapi.php`
(`api.sehavniva.no` is retired; don't use.)
**Licence:** CC BY 4.0. Attribution to "Kartverket" required. <https://creativecommons.org/licenses/by/4.0/>
**Attribution:** "Tidal data © Norwegian Mapping Authority, Hydrographic Service (Kartverket), CC BY 4.0".
**Spec:** [API for water level and tides — communication protocol (PDF, rev. June 2025)](https://vannstand.kartverket.no/API%20for%20water%20level%20and%20tides%20-%20communication%20protocol_revJune2025.pdf)
**Docs:** <https://vannstand.kartverket.no/tideapi_en.html>

### Requests

| Need | `tide_request=` | Params |
|------|-----------------|--------|
| Events | `locationdata` | `lat`, `lon`, `fromtime`, `totime`, `datatype=tab`, `refcode=cd`, `tzone=0` |
| Curve | `locationdata` | as above, `datatype=pre`, `interval=10` |
| Observed | `locationdata` | `datatype=obs` (from the zone's nearest permanent gauge) |
| Stations | `stationlist` | `type=perm` — optional; the API is coordinate-based |

### Response shape

```xml
<tide><locationdata>
  <location name="Stavanger" code="SVG" latitude="…" longitude="…" delay="0" factor="1.00" obscode="SVG"/>
  <reflevelcode>CD</reflevelcode>
  <data type="prediction" unit="cm" qualityFlag="1" …>
    <waterlevel value="40.9" time="2026-09-14T05:01:00+00:00" flag="low"/>
```

### Limits

- Per request: ≤ 366 days of data, ≤ 1000 days of high/low. Longer is
  silently truncated.
- Capacity: "about 20 requests per second" *shared by all users*. Cache;
  keep requests to the minimum.

### Notes

- **Unit is cm.** Provider divides by 100.
- **`tzone` defaults to 1 (UTC+1).** Always pass `tzone=0`, and parse the
  ISO offset anyway.
- Coordinate-based: any Norwegian coastal position resolves to a tidal zone;
  the zone applies `factor`/`delay` to a reference station's harmonics and
  adds surge from `obscode`. Positions outside all zones return an error —
  map to `StationNotFound`.
- `refcode`: `cd` (chart datum, default), `msl`, `nn2000`. CD/NN2000 are not
  defined everywhere.
- `qualityFlag` in the response: surface as an attribute if cheap; don't
  block on it.
- Also exposes `constituents` for a station — future offline-harmonic slot.
- Terms: <https://www.kartverket.no/en/api-and-data/terms-of-use>. Data page: <https://www.kartverket.no/en/api-and-data/tides-and-water-level-data>.
- MET Norway's `api.met.no/weatherapi/tidalwater` republishes the same
  predictions; not a separate provider.

---

## Candidates (not planned for v1)

Ranked by how cleanly they fit the contract. See
[api-landscape.md](api-landscape.md) for the survey.

| Slug | Source | Fit | Blocker |
|------|--------|-----|---------|
| `dmi` | DMI oceanObs (DK, GL, FO) | good | none; OGC API Features, CC BY 4.0, no key |
| `bsh` | BSH WaterLevelForecast (DE) | good | endpoint marked "may change"; forecast not pure astronomical tide |
| `chs` | CHS IWLS (CA) | ok | licence is non-commercial-only, no navigation; 3 req/s, 30 req/min |
| `rws` | Rijkswaterstaat WaterWebservices (NL) | ok | new API Dec 2025, SOAP-ish JSON; NAP datum |
| `linz` | LINZ (NZ) | poor | CSV files per station-year, no API |
| `bom` | BoM (AU) | poor | registered data service; Crown copyright terms |
| `ukho` | Admiralty UK Tidal API | **no** | Discovery tier forbids caching; violates non-negotiable #2 |
| `shom` | SHOM (FR) | **no** | paid subscription key |
| `worldtides` | worldtides.info | **no** | paid per request; not an official source |
