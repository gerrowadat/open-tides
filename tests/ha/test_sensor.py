"""Entity states derived from a fixed event list."""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant

from custom_components.open_tides.const import OPT_ENABLE_CURVE, OPT_ENABLE_OBSERVED
from pyopentides import Observation

from .conftest import NOW, FakeProvider, station_entry


async def _setup(hass: HomeAssistant, options: dict[str, object] | None = None) -> None:
    entry = station_entry(options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_core_entities(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    await _setup(hass)

    tide = hass.states.get("sensor.testport_tide")
    assert tide is not None
    assert tide.state == "rising"
    a = tide.attributes
    assert a["datum"] == "LAT"
    assert a["provider"] == "fake"
    assert a["station"] == "Testport"
    assert a["attribution"] == "Fake data (test)"
    assert a["licence"] == "CC-BY-4.0"
    assert a["licence_url"].startswith("https://")
    assert "curve" not in a
    events = a["events"]
    assert events[0] == {
        "time": "2026-09-14T16:12:00+00:00",
        "height": 4.0,
        "type": "high",
    }
    assert all(set(e) == {"time", "height", "type"} for e in events)
    assert events[-1]["time"] <= "2026-09-16T12:00:00+00:00"

    assert (
        hass.states.get("sensor.testport_next_high").state
        == "2026-09-14T16:12:00+00:00"
    )
    assert (
        hass.states.get("sensor.testport_next_low").state == "2026-09-14T22:24:00+00:00"
    )
    assert float(hass.states.get("sensor.testport_next_high_height").state) == 4.0
    assert float(hass.states.get("sensor.testport_next_low_height").state) == 0.5
    assert hass.states.get("sensor.testport_predicted_height") is None


async def test_state_flips_after_high(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    freezer.move_to(NOW)
    await _setup(hass)
    freezer.move_to(NOW + timedelta(hours=5))  # 17:00, past the 16:12 high
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    # Entities re-evaluate on coordinator update; force one without a fetch.
    entry = hass.config_entries.async_entries("open_tides")[0]
    entry.runtime_data.coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.testport_tide").state == "falling"
    assert (
        hass.states.get("sensor.testport_next_high").state
        == "2026-09-15T04:36:00+00:00"
    )


async def test_curve_entities(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    await _setup(hass, {OPT_ENABLE_CURVE: True})
    curve = hass.states.get("sensor.testport_tide").attributes["curve"]
    assert curve and isinstance(curve[0], list) and len(curve[0]) == 2
    assert curve[0][0] == NOW.isoformat()
    # 48 h at 20-min step
    assert 140 <= len(curve) <= 145
    predicted = float(hass.states.get("sensor.testport_predicted_height").state)
    # Fake curve ramps 1.0→3.0 from (now - 2 d) to (now + 12 h + 48 h); at now:
    span = timedelta(days=2) + timedelta(hours=12) + timedelta(hours=48)
    assert predicted == pytest.approx(1.0 + 2.0 * timedelta(days=2) / span, abs=0.01)


async def test_observed_and_surge(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    await _setup(hass, {OPT_ENABLE_OBSERVED: True})
    obs = hass.states.get("sensor.testport_observed_height")
    assert float(obs.state) == 2.5
    assert obs.attributes["observed_at"] == (NOW - timedelta(minutes=5)).isoformat()
    assert obs.attributes["attribution"] == "Fake data (test)"
    surge = float(hass.states.get("sensor.testport_surge").state)
    # No curve: predicted is the cosine between 10:00 low (0.5) and 16:12 high (4.0).
    from custom_components.open_tides import tide as tide_math

    entry = hass.config_entries.async_entries("open_tides")[0]
    events = entry.runtime_data.coordinator.data.events
    predicted = tide_math.predicted_at(events, [], NOW - timedelta(minutes=5))
    assert surge == pytest.approx(2.5 - predicted, abs=0.001)


async def test_observed_none(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    FakeProvider.observation = None
    await _setup(hass, {OPT_ENABLE_OBSERVED: True})
    assert hass.states.get("sensor.testport_observed_height").state == "unknown"
    assert hass.states.get("sensor.testport_surge").state == "unknown"


async def test_entity_ids_ignore_area_naming(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Device in an area; the naming scheme may prefix it. Ours must not."""
    from homeassistant.helpers import area_registry as ar
    from homeassistant.helpers import device_registry as dr

    freezer.move_to(NOW)
    entry = station_entry({OPT_ENABLE_CURVE: True, OPT_ENABLE_OBSERVED: True})
    entry.add_to_hass(hass)
    area = ar.async_get(hass).async_get_or_create("Back Garden")
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("open_tides", entry.entry_id)},
        name="Testport",
        suggested_area=area.name,
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ids = {s.entity_id for s in hass.states.async_all("sensor")}
    assert {
        "sensor.testport_tide",
        "sensor.testport_next_high",
        "sensor.testport_next_low",
        "sensor.testport_next_high_height",
        "sensor.testport_next_low_height",
        "sensor.testport_predicted_height",
        "sensor.testport_observed_height",
        "sensor.testport_surge",
    } <= ids
    assert not any("back_garden" in i for i in ids)


async def test_surge_with_stale_observation(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Marine Institute observations lag ~30 h; surge must still resolve."""
    freezer.move_to(NOW)
    FakeProvider.observation = Observation(time=NOW - timedelta(hours=30), height_m=2.0)
    await _setup(hass, {OPT_ENABLE_OBSERVED: True})
    assert hass.states.get("sensor.testport_surge").state != "unknown"
