# Graphing

<!-- PLACEHOLDER: no card ships in v1. This page documents how to plot the
     `curve` and `events` attributes with existing community cards. -->

`sensor.<name>_tide` exposes `events` (next 48 h of highs/lows) and, when
the curve option is enabled, `curve` (next 48 h at 20-minute steps). Both
are documented in [design.md](design.md#entities) and are a public contract.

## ApexCharts card

<!-- TODO: working config using `data_generator` over the `curve` attribute,
     with high/low events as annotations. Verify against a live install. -->

```yaml
type: custom:apexcharts-card
# TODO
```

## TideWise card

<!-- TODO: config for TideWise generic-sensor mode pointing at
     `sensor.<name>_tide`. Verify the `events` shape against TideWise's
     current docs before release — adjust *our* shape, not theirs. -->

```yaml
# TODO
```
