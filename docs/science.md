# The science bit

Enough to read the code and the provider docs. For more, the links.

## What a tide is

The Moon and Sun pull on the ocean. The pull varies across the Earth's
diameter, which stretches the water into two bulges; the Earth rotates under
them. That gives roughly two highs and two lows a day (semidiurnal), with the
Moon's ~12h25m dominating — which is why tides drift ~50 minutes later each
day.

Add: the Sun (spring tides when aligned with the Moon, neaps when at right
angles), the Moon's elliptical and inclined orbit, and 18.6-year nodal cycle.
Then the real shape of the ocean basins: resonance, friction, Coriolis,
coastlines. The result at any coast is *not* the textbook bulge — it's the
basin's response to the forcing. Some places get one tide a day (diurnal),
some get mixed, some almost none (amphidromic points).

Readable: NOAA, [Our Restless Tides](https://tidesandcurrents.noaa.gov/restles1.html);
NOAA NOS, [Tides and Water Levels tutorial](https://oceanservice.noaa.gov/education/tutorial_tides/).

## Harmonic analysis

The forcing is astronomical, therefore periodic, therefore expressible as a
sum of cosines with *known frequencies*. Each is a **constituent**: M2 (main
lunar semidiurnal), S2 (solar), N2 (lunar elliptic), K1, O1 (diurnal), and so
on to hundreds of minor and shallow-water terms. Frequencies are universal;
what varies per location is each constituent's **amplitude** and **phase
lag**. Those two numbers per constituent are the *harmonic constants*.

Fit a year or more of gauge data by least squares → constants. Evaluate the
sum at any future time → prediction. That's the whole method. Agencies do the
fit; tide tables are the evaluation.

$$h(t) = Z_0 + \sum_i f_i H_i \cos(\omega_i t + (V_0+u)_i - g_i)$$

$Z_0$ mean level, $H_i, g_i$ amplitude and phase, $f_i, u_i$ nodal
corrections, $V_0$ astronomical argument.

- Method: Parker, [*Tidal Analysis and Prediction*](https://tidesandcurrents.noaa.gov/publications/Tidal_Analysis_and_Predictions.pdf), NOAA NOS CO-OPS 3 (2007). The standard reference; free.
- Book: Pugh & Woodworth, *Sea-Level Science* (CUP, 2014). The textbook.
- Code: [UTide](https://github.com/wesleybowman/UTide) (Python), [pytides](https://github.com/sam-cox/pytides), [XTide](https://flaterco.com/xtide/) (the classic offline predictor).
- Global models from altimetry: [FES2022](https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html). Used where there is no gauge — e.g. the Marine Institute's surge product falls back to FES2014, and its `_MODELLED` stations come from a hydrodynamic model.

**Why this matters for us:** predictions are deterministic and cheap to
compute. Agencies publish years ahead. Nothing about a prediction changes
between Monday and Tuesday. Hence `min_refresh` in days, not minutes.

## Prediction vs. observation vs. forecast

- **Prediction**: astronomical tide from harmonics. Weather ignored.
- **Observation**: gauge reading. Prediction + weather + everything else.
- **Surge** (residual): observation − prediction. Wind and pressure, mostly.
  A deep low can add a metre.
- **Forecast**: prediction + modelled surge from a weather model, ~3 days out.

`sensor.<name>_surge` is the residual. It's the single most useful number for
"is today unusual".

## Datums

A height is meaningless without a zero. Agencies pick one per station.

| Datum | Definition |
|-------|-----------|
| **LAT** | Lowest Astronomical Tide. Lowest level predictable under average weather over the 19-year nodal cycle. IHO-recommended chart datum ([IHO Resolution 3/1919](https://iho.int/en/standards-and-specifications)). Predictions are ≥ 0 by construction; surge can go below |
| **HAT** | Highest Astronomical Tide. Bridge clearances |
| **Chart Datum (CD)** | Whatever the chart uses. Usually LAT or close. Local |
| **MLLW** | Mean of the lower of the two daily lows over the epoch. US chart datum |
| **MLW, MHW, MHHW** | Other tidal means. MHHW is the US flooding reference |
| **MSL** | Mean sea level over the epoch |
| **Land datums** | OD Malin (IE), NAP (NL), NN2000 (NO), NAVD88 (US), OD Newlyn (UK). Surveyor's zero. Tide levels go negative |

The **epoch** matters: NOAA's National Tidal Datum Epoch is 1983–2001, being
updated. Sea-level rise moves everything relative to land datums.

Conversions are per-station lookup tables published by the agency. There is
no formula. That's why the contract forbids converting and requires
declaring.

- NOAA, [Tidal Datums](https://tidesandcurrents.noaa.gov/datum_options.html)
- NOAA, [Tidal Datums and Their Applications](https://tidesandcurrents.noaa.gov/publications/tidal_datums_and_their_applications.pdf) (NOS CO-OPS 1)

## What tide-watchers know

The vocabulary in almanacs and on the quay.

- **Springs and neaps.** Range swells and shrinks on a ~14.8-day cycle as the
  Sun's pull (S2) drifts in and out of step with the Moon's (M2). Springs a
  day or two after new and full moon; neaps after the quarters. "Spring" is
  from *springing up*, nothing to do with the season. Almanacs print MHWS /
  MLWS / MHWN / MLWN per port so you can see where today sits.
- **Range beats height.** Big range means strong streams, fast-draining
  flats, moorings that dry. `sensor.<name>_range` and its `horizon_max` /
  `horizon_min` attributes give today's range against the port's springs
  and neaps; `next_spring` / `next_neap` say when.
- **Slack water** is the pause at the turn, when streams stop. In narrows and
  harbour mouths it can lag high or low water by an hour or more. `rate`
  goes through zero there.
- **Rule of twelfths.** Rise per hour after low water: 1/12, 2/12, 3/12,
  3/12, 2/12, 1/12 of the range. Half the water moves in the middle two
  hours; that's the strongest flow. `rate` is the continuous version.
- **Tidal coefficient.** French, Spanish and Portuguese tables scale the
  range 20–120: ≥ 95 *vive-eau* (big springs), ~45 *morte-eau* (neaps), 120
  the largest possible. Not exposed yet.
- **King tides** are the year's largest springs — perigee coinciding with an
  equinoctial spring. `next_spring` over a 90-day horizon finds the season's
  biggest, not necessarily the year's.
- **Depth = chart depth + height above datum.** Charted depths are below
  LAT/CD; the prediction adds to them. A negative low (land datums, or under
  a negative surge) means less than the chart says.
- **Surge.** Weather moves the sea off the prediction: a deep low adds tens
  of centimetres, a bad one a metre. `surge` is observed − predicted. It's
  what the harbour master watches.
- **Regime.** Two near-equal tides a day (semidiurnal: Europe), one (diurnal:
  Gulf of Mexico), or two unequal ones (mixed: US west coast, where NOAA marks
  HH/LL). In a mixed regime "next high" may be the small one.
- **Daily lag** ~50 min later each day, from the Moon's orbit. Tuesday's
  14:00 high is Friday's ~16:30.

## Interpolating between highs and lows

If you only have events, the "rule of twelfths" (1/12, 2/12, 3/12, 3/12,
2/12, 1/12 of the range per hour over a ~6 h half-cycle) is a cosine
approximation. A real cosine between adjacent events is better and trivial:

$$h(t) = \frac{h_1+h_2}{2} + \frac{h_1-h_2}{2}\cos\!\left(\pi\,\frac{t-t_1}{t_2-t_1}\right)$$

Good to ~10 cm in semidiurnal regimes; poor where the curve is asymmetric
(estuaries, shallow water, double highs like Southampton). Prefer the
provider's curve when the user has enabled it.

## Gauges

A tide gauge is a stilling well + float, a pressure sensor, or a radar
altimeter on a pier, sampled every 1–6 min, referenced to benchmarks that are
themselves levelled to the national datum. Networks: national (INTGN, NWLON,
Kartverket's permanent stations), federated in [GLOSS](https://gloss-sealevel.org/)
and the [IOC Sea Level Station Monitoring Facility](https://www.ioc-sealevelmonitoring.org/).
Long records go to [PSMSL](https://psmsl.org/).

## Further

- Pugh & Woodworth, *Sea-Level Science*, CUP 2014.
- PSMSL reading list: <https://psmsl.org/train_and_info/training/reading/books.php>
- NOAA CO-OPS publications: <https://tidesandcurrents.noaa.gov/pub.html>
- Doodson (1921), the original constituent catalogue. Historical interest.
