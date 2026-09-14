# How tide providers expose data

A survey of the API space, as of 2026-09-14. Why the provider contract looks
the way it does. Per-provider detail: [providers.md](providers.md). Science:
[science.md](science.md).

## Who publishes tides

National hydrographic offices (or the met/ocean agency that does it for them)
hold the gauge networks and the harmonic constants. They publish:

1. **Tide tables** — high/low water times and heights. The oldest product;
   every agency has it.
2. **Predicted curves** — level at a fixed step (5–60 min) from the harmonics.
3. **Observations** — what the gauge actually reads, minutes old.
4. **Forecasts** — prediction + modelled surge, a few days ahead.
5. **Constituents** — the harmonic constants themselves, for offline prediction.

Everything a consumer wants is (1) and sometimes (2). (3) is a bonus. (4) and
(5) are out of scope here.

## Transport shapes seen in the wild

| Shape | Examples | Notes |
|-------|----------|-------|
| Bespoke REST, JSON/CSV | NOAA CO-OPS, CHS IWLS | Query params, station id, date range, product name |
| ERDDAP `tabledap` | Marine Institute (IE) | OPeNDAP-style constraint URL, any output format. Common in ocean science; several agencies run one |
| Bespoke XML | Kartverket (NO) | `tideapi.php?tide_request=…`; coordinate-based |
| OGC API Features (GeoJSON) | DMI (DK), BSH (DE) | Newer government portals converge here |
| Yearly CSV/PDF per station | LINZ (NZ), BoM (AU), IH (PT) | No API; scrape or bundle |
| Paid API with key | UKHO Admiralty, SHOM, worldtides.info | Terms restrict caching or charge per call |

The contract in [design.md](design.md) deliberately ignores transport. A
provider module owns its HTTP; the core sees events and points.

## Station vs. coordinate

- **Station-based** (NOAA, MI, CHS, DMI, BSH): a finite list with ids. User
  picks one. Predictions are only valid *at* the gauge.
- **Coordinate-based** (Kartverket): the agency has divided the coast into
  zones, each mapped to a reference station with a time delay and height
  factor. Any lat/lon resolves to a zone. NOAA's "subordinate stations" are the
  same idea with a fixed list.

Both are the same contract: `Location` is either.

## Datums

Every agency picks a vertical reference. Consumers can't convert between them
without the agency's own offset table.

| Datum | Used by | Meaning |
|-------|---------|---------|
| LAT | IE, UK, AU, NZ, most IHO members | Lowest Astronomical Tide. IHO-recommended chart datum |
| CD | NO, CA, FR | Chart Datum — usually LAT or close to it, locally defined |
| MLLW | US | Mean Lower Low Water over the 19-year epoch |
| MSL | some model outputs | Mean sea level; useless for "will I ground" |
| ODM, DVR90, NAP, NN2000, NAVD88 | IE, DK, NL, NO, US | Land-survey datums. Levels can be negative |

This is why the contract says *declare, don't convert*. See
[science.md § Datums](science.md#datums).

## Politeness expectations

What the agencies actually say:

| Agency | Stated limit | Guidance |
|--------|--------------|----------|
| NOAA | none published | "throttling applies to heavy loads"; send `application=`; sleep between calls |
| Marine Institute | none published | shared research ERDDAP; nothing in legal notice |
| Kartverket | ~20 req/s shared by everyone | "cache static data locally and limit requests to a necessary minimum" |
| CHS | 3 req/s, 30 req/min, HTTP 429 | hard-enforced |
| DMI | none; may throttle by IP | "align refresh with the update cycle; cache" |
| UKHO | tier quotas | Discovery tier: caching is a copyright breach |

Predictions don't change. Constituents are re-derived rarely; a station's
tables are published a year ahead. Polling more than once a day is never
justified, and once a week is fine for a 90-day horizon. That is the basis for
`min_refresh` and the `Store`-first startup rule.

## Licences

| Licence | Agencies | Cache | Redistribute | Attribution |
|---------|----------|-------|--------------|-------------|
| Public domain (US Gov) | NOAA | yes | yes | requested |
| CC BY 4.0 | MI, Kartverket, DMI, BSH, LINZ | yes | yes | required |
| DL-DE BY 2.0 | some German federal data | yes | yes | required |
| Licence Ouverte 2.0 | some SHOM datasets (not the tide API) | yes | yes | required |
| CHS licence | CHS | unclear | non-commercial only, no navigation | required, fixed wording |
| UKHO API T&Cs | Admiralty | tier-dependent | no | — |
| Crown copyright (AU) | BoM | conditions of use | conditions of use | required |

`attribution` on the provider class is the licence's attribution clause. It
goes on every entity.

## Existing HA integrations, for comparison

| Integration | Source | Caches? | Notes |
|-------------|--------|---------|-------|
| `noaa_tides` (core) | NOAA | no | YAML only; US only |
| `worldtidesinfo` (core) | worldtides.info | no | paid per call |
| `worldtidesinfocustom` | worldtides.info | yes | credit-aware, curve |
| `ha-norwegiantide` | Kartverket | partial | NO only |
| `HASS-ukho_tides` | Admiralty | no (can't) | UK only |
| `ha-bsh_tides` | BSH | ? | DE only |
| TideWise (card) | NOAA direct, or any sensor | — | `generic_entity` mode reads `events`/`predictions` with `time`/`height`/`type` |

Our `events` attribute shape matches TideWise `generic_entity`. Keep it that
way; see [design.md § Entities](design.md#entities).

## Sources

- NOAA CO-OPS Data API: <https://api.tidesandcurrents.noaa.gov/api/prod/>
- NOAA CO-OPS Metadata API: <https://api.tidesandcurrents.noaa.gov/mdapi/prod/>
- Marine Institute ERDDAP: <https://erddap.marine.ie/erddap/>
- ERDDAP tabledap docs: <https://erddap.github.io/docs/user/tabledap>
- Kartverket API: <https://vannstand.kartverket.no/tideapi_en.html>
- CHS web services: <https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service>
- DMI oceanObs API: <https://www.dmi.dk/friedata/dokumentation/apis/oceanographic-observation-and-tidewater-api>
- BSH water levels: <https://wasserstand.bsh.de/>
- UKHO Admiralty API FAQ: <https://developer.admiralty.co.uk/faqs>
- SHOM tide services: <https://services.data.shom.fr/support/en/services/spm>
- LINZ tide predictions: <https://www.linz.govt.nz/products-services/tides-and-tidal-streams/tide-predictions>
- BoM tides: <https://www.bom.gov.au/australia/tides/>
- TideWise: <https://github.com/TheWillMiller/tide-wise>
