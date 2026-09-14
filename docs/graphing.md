# Graphing

No card ships. `sensor.<name>_tide` carries the data; these cards draw it.

Attributes (public contract, see [design.md](design.md#entities)):

```yaml
events:                          # next 48 h
  - time: 2026-09-14T16:12:00+00:00
    height: 4.0
    type: high
curve:                           # next 48 h, 20-min step; only with the curve option on
  - ["2026-09-14T12:00:00+00:00", 2.31]
```

## TideWise

[TideWise](https://github.com/TheWillMiller/tide-wise) reads `events`
directly in `generic_entity` mode.

```yaml
type: custom:tide-wise-card
provider: generic_entity
tide_entity: sensor.dublin_port_tide
tide_time_mode: as_is
units: metric
```

## ApexCharts

[apexcharts-card](https://github.com/RomRider/apexcharts-card) with
`data_generator`. Needs the curve option enabled.

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: minute
header:
  show: true
  title: Dublin Port tide
yaxis:
  - min: 0
    decimals: 1
series:
  - entity: sensor.dublin_port_tide
    name: Predicted
    type: area
    stroke_width: 2
    data_generator: |
      return entity.attributes.curve.map(p => [new Date(p[0]).getTime(), p[1]]);
  - entity: sensor.dublin_port_tide
    name: High / low
    type: scatter
    data_generator: |
      return entity.attributes.events.map(e => [new Date(e.time).getTime(), e.height]);
now:
  show: true
```

Without the curve, plot `events` alone as `type: line` with
`curve: smooth` — close enough for a glance, wrong in detail.
