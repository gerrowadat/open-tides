from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.open_tides.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PROVIDER,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    DOMAIN,
    OPT_ENABLE_CURVE,
    OPT_ENABLE_OBSERVED,
    OPT_REFRESH_HOURS,
)
from pyopentides import ProviderUnavailable

from .conftest import FakeProvider, station_entry


async def test_station_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROVIDER: "fake"}
    )
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "station"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STATION_ID: "st1"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Testport"
    assert result["data"] == {
        CONF_PROVIDER: "fake",
        CONF_STATION_ID: "st1",
        CONF_STATION_NAME: "Testport",
        CONF_LATITUDE: 53.0,
        CONF_LONGITUDE: -6.0,
    }
    assert result["result"].unique_id == "fake:st1"
    await hass.async_block_till_done()


async def test_coordinate_flow_defaults_to_home(hass: HomeAssistant) -> None:
    hass.config.latitude, hass.config.longitude = 58.97, 5.73
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROVIDER: "fake_coords"}
    )
    assert result["step_id"] == "coordinates"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"location": {CONF_LATITUDE: 58.97, CONF_LONGITUDE: 5.73}},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "58.970, 5.730"
    assert result["data"][CONF_STATION_ID] is None
    assert result["result"].unique_id == "fake_coords:58.970,5.730"
    await hass.async_block_till_done()


async def test_duplicate_station_aborts(hass: HomeAssistant) -> None:
    station_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROVIDER: "fake"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STATION_ID: "st1"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_station_list_failure(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(self: FakeProvider) -> None:
        raise ProviderUnavailable("down")

    monkeypatch.setattr(FakeProvider, "list_stations", boom)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROVIDER: "fake"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_enforces_floor(hass: HomeAssistant) -> None:
    entry = station_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    # Fake floor is 12 h. The selector's min rejects it before our own check.
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {OPT_REFRESH_HOURS: 1, OPT_ENABLE_CURVE: False, OPT_ENABLE_OBSERVED: False},
        )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {OPT_REFRESH_HOURS: 24, OPT_ENABLE_CURVE: True, OPT_ENABLE_OBSERVED: False},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[OPT_REFRESH_HOURS] == 24
    assert entry.options[OPT_ENABLE_CURVE] is True
