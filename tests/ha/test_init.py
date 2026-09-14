"""Setup, store round-trip, floor enforcement, refresh service."""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.open_tides.const import (
    DOMAIN,
    OPT_ENABLE_CURVE,
    OPT_ENABLE_OBSERVED,
    OPT_REFRESH_HOURS,
    SERVICE_REFRESH,
)
from custom_components.open_tides.coordinator import refresh_interval
from pyopentides import Capabilities, ProviderUnavailable

from .conftest import NOW, FakeProvider, station_entry


async def test_setup_fetches_once_and_persists(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = station_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert FakeProvider.calls == {"capabilities": 1, "get_events": 1}
    assert hass.states.get("sensor.testport_tide") is not None

    # Restart: unload + reload must not fetch again.
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    FakeProvider.calls = {}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert FakeProvider.calls == {"capabilities": 1}
    assert hass.states.get("sensor.testport_tide").state == "rising"


async def test_stale_cache_refetches(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = station_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)

    # Horizon is 30 d; cache is stale once less than 15 d remain.
    freezer.move_to(NOW + timedelta(days=20))
    FakeProvider.calls = {}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert FakeProvider.calls.get("get_events") == 1


async def test_scheduled_refresh_respects_interval(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    freezer.move_to(NOW)
    entry = station_entry({OPT_REFRESH_HOURS: 24})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    FakeProvider.calls = {}

    freezer.tick(timedelta(hours=23))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert FakeProvider.calls.get("get_events") is None

    freezer.tick(timedelta(hours=1, minutes=24 * 60 * 0.1 + 1))  # past jitter
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert FakeProvider.calls.get("get_events") == 1


def test_refresh_interval_floor() -> None:
    assert refresh_interval(FakeProvider, {}) == timedelta(hours=12)
    assert refresh_interval(FakeProvider, {OPT_REFRESH_HOURS: 1}) == timedelta(hours=12)
    assert refresh_interval(FakeProvider, {OPT_REFRESH_HOURS: 48}) == timedelta(
        hours=48
    )


async def test_refresh_service_honours_floor(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    freezer.move_to(NOW)
    entry = station_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    FakeProvider.calls = {}

    await hass.services.async_call(DOMAIN, SERVICE_REFRESH, blocking=True)
    assert FakeProvider.calls.get("get_events") is None
    assert "refresh refused" in caplog.text

    freezer.tick(timedelta(hours=13))
    await hass.services.async_call(DOMAIN, SERVICE_REFRESH, blocking=True)
    assert FakeProvider.calls.get("get_events") == 1


async def test_curve_and_observed_options(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    entry = station_entry({OPT_ENABLE_CURVE: True, OPT_ENABLE_OBSERVED: True})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert FakeProvider.calls == {
        "capabilities": 1,
        "get_events": 1,
        "get_curve": 1,
        "get_observed": 1,
    }
    assert hass.states.get("sensor.testport_predicted_height") is not None
    assert hass.states.get("sensor.testport_observed_height") is not None
    assert hass.states.get("sensor.testport_surge") is not None


async def test_options_ignored_when_unsupported(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    FakeProvider.caps = Capabilities(curve=False, observed=False)
    entry = station_entry({OPT_ENABLE_CURVE: True, OPT_ENABLE_OBSERVED: True})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert "get_curve" not in FakeProvider.calls
    assert "get_observed" not in FakeProvider.calls
    assert hass.states.get("sensor.testport_predicted_height") is None
    assert hass.states.get("sensor.testport_observed_height") is None


async def test_provider_down_at_first_setup_retries(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(self: FakeProvider, *a: object) -> None:
        raise ProviderUnavailable("down")

    monkeypatch.setattr(FakeProvider, "get_events", boom)
    entry = station_entry()
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
