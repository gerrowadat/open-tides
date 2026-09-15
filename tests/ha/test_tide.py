"""Pure derivations in custom_components.open_tides.tide."""

from __future__ import annotations

import math
from datetime import timedelta

import pytest

from custom_components.open_tides import tide
from pyopentides import Point, TideEvent

from .conftest import HALF_CYCLE, NOW, make_curve, make_events

EVENTS = make_events(NOW - timedelta(days=1), NOW + timedelta(days=2))


def test_bracket() -> None:
    prev, nxt = tide.bracket(EVENTS, NOW)
    assert prev is not None and nxt is not None
    assert prev.time <= NOW < nxt.time
    assert nxt.time - prev.time == HALF_CYCLE


def test_state_and_next() -> None:
    # 14th: 03:48 high, 10:00 low, 16:12 high, 22:24 low → at 12:00 rising.
    assert tide.state(EVENTS, NOW) == "rising"
    nh = tide.next_of(EVENTS, "high", NOW)
    nl = tide.next_of(EVENTS, "low", NOW)
    assert nh and nh.time.isoformat() == "2026-09-14T16:12:00+00:00"
    assert nl and nl.time.isoformat() == "2026-09-14T22:24:00+00:00"


def test_state_none_after_last_event() -> None:
    assert tide.state(EVENTS, EVENTS[-1].time + timedelta(hours=1)) is None


def test_cosine_midpoint_is_mean() -> None:
    a = TideEvent(NOW, 4.0, "high")
    b = TideEvent(NOW + HALF_CYCLE, 0.5, "low")
    assert tide.cosine_between(a, b, NOW) == pytest.approx(4.0)
    assert tide.cosine_between(a, b, NOW + HALF_CYCLE / 2) == pytest.approx(2.25)
    assert tide.cosine_between(a, b, NOW + HALF_CYCLE) == pytest.approx(0.5)


def test_interpolate_curve() -> None:
    curve = make_curve(NOW, NOW + timedelta(hours=1))
    assert tide.interpolate_curve(curve, NOW) == pytest.approx(1.0)
    assert tide.interpolate_curve(curve, NOW + timedelta(minutes=30)) == pytest.approx(
        2.0
    )
    assert tide.interpolate_curve(curve, NOW + timedelta(minutes=5)) == pytest.approx(
        1.0 + 2.0 / 12
    )
    assert tide.interpolate_curve(curve, NOW - timedelta(minutes=1)) is None
    assert tide.interpolate_curve([], NOW) is None


def test_predicted_at_prefers_curve_then_cosine() -> None:
    curve = make_curve(NOW, NOW + timedelta(hours=1))
    assert tide.predicted_at(EVENTS, curve, NOW) == pytest.approx(1.0)
    outside = NOW + timedelta(hours=2)
    prev, nxt = tide.bracket(EVENTS, outside)
    assert prev and nxt
    assert tide.predicted_at(EVENTS, curve, outside) == pytest.approx(
        tide.cosine_between(prev, nxt, outside)
    )


def test_window_and_downsample() -> None:
    assert all(
        NOW <= e.time <= NOW + timedelta(hours=48)
        for e in tide.window(EVENTS, NOW, timedelta(hours=48))
    )
    curve = make_curve(NOW - timedelta(hours=1), NOW + timedelta(hours=3))
    thinned = tide.downsample(curve, NOW, timedelta(hours=2), timedelta(minutes=20))
    assert thinned[0].time == NOW
    assert thinned[-1].time <= NOW + timedelta(hours=2)
    gaps = {thinned[i + 1].time - thinned[i].time for i in range(len(thinned) - 1)}
    assert gaps == {timedelta(minutes=20)}
    assert tide.downsample(
        [Point(NOW, 1.0)], NOW, timedelta(hours=1), timedelta(minutes=20)
    ) == [Point(NOW, 1.0)]


MOD = make_events(NOW - timedelta(days=1), NOW + timedelta(days=40), modulate=True)


def test_ranges_and_current_range() -> None:
    rs = tide.ranges(EVENTS)
    assert len(rs) == len(EVENTS) - 1
    assert all(r == pytest.approx(3.5) for _, _, r in rs)
    assert tide.current_range(EVENTS, NOW) == pytest.approx(3.5)
    assert tide.current_range(EVENTS, EVENTS[-1].time + timedelta(hours=1)) is None


def test_spring_and_neap_found_in_window() -> None:
    from .conftest import SPRING_AT

    spring = tide.extreme_range(MOD, NOW, largest=True)
    neap = tide.extreme_range(MOD, NOW, largest=False)
    assert spring and neap
    assert spring[0].kind == "high" and neap[0].kind == "high"
    assert abs(spring[0].time - SPRING_AT) < timedelta(hours=7)
    assert spring[1] == pytest.approx(4.5, abs=0.02)
    in_window = [
        r
        for _, b, r in tide.ranges(MOD)
        if NOW <= b.time <= NOW + tide.SPRING_NEAP_WINDOW
    ]
    assert neap[1] == pytest.approx(min(in_window))
    assert spring[1] == pytest.approx(max(in_window))


def test_extreme_range_none_outside_events() -> None:
    assert (
        tide.extreme_range(EVENTS, EVENTS[-1].time + timedelta(days=1), largest=True)
        is None
    )


def test_rate_sign_and_zero_at_turn() -> None:
    # 10:00 low → 16:12 high on the 14th: rising at NOW (12:00), zero at the high.
    assert tide.rate(EVENTS, [], NOW) > 0
    high = tide.next_of(EVENTS, "high", NOW)
    assert high is not None
    assert tide.rate(EVENTS, [], high.time) == pytest.approx(0.0, abs=1e-6)
    assert tide.rate(EVENTS, [], high.time + timedelta(hours=3)) < 0
    # Mid-tide (3h06m after the low) is the fastest: range/2 * pi / half-cycle.
    mid = high.time - HALF_CYCLE / 2
    expected = 3.5 / 2 * math.pi / (HALF_CYCLE.total_seconds() / 3600)
    assert tide.rate(EVENTS, [], mid) == pytest.approx(expected, rel=0.01)


def test_rate_none_without_bracket() -> None:
    assert tide.rate(EVENTS, [], EVENTS[-1].time + timedelta(days=1)) is None
