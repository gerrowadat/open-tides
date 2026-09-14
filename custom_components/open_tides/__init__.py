"""Open Tides — tide predictions from official national sources."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from pyopentides import Location
from pyopentides.providers import PROVIDERS

from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PROVIDER,
    CONF_STATION_ID,
    DOMAIN,
    SERVICE_REFRESH,
)
from .coordinator import ObservedCoordinator, TideCoordinator, remove_store

if TYPE_CHECKING:
    from pyopentides import TideProvider

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class OpenTidesData:
    provider: TideProvider
    location: Location
    coordinator: TideCoordinator
    observed: ObservedCoordinator | None


type OpenTidesConfigEntry = ConfigEntry[OpenTidesData]


def integration_version(hass: HomeAssistant) -> str:
    from homeassistant.loader import async_get_loaded_integration

    try:
        return str(async_get_loaded_integration(hass, DOMAIN).version or "0")
    except Exception:
        return "0"


def location_from_entry(entry: ConfigEntry) -> Location:
    if entry.data.get(CONF_STATION_ID):
        return Location(station_id=entry.data[CONF_STATION_ID])
    return Location(lat=entry.data[CONF_LATITUDE], lon=entry.data[CONF_LONGITUDE])


async def async_setup(hass: HomeAssistant, config: dict) -> bool:  # type: ignore[type-arg]
    """Register the refresh service once."""

    async def _refresh(call: ServiceCall) -> None:
        entry_ids = call.data.get("entry_id")
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry_ids and entry.entry_id not in entry_ids:
                continue
            if entry.state.recoverable is False or not hasattr(entry, "runtime_data"):
                continue
            coord = entry.runtime_data.coordinator
            if not coord.can_refresh_now():
                _LOGGER.warning(
                    "%s: refresh refused; %s allows one fetch per %s",
                    entry.title,
                    coord.provider.name,
                    coord.provider.min_refresh,
                )
                continue
            await coord.async_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        _refresh,
        schema=vol.Schema(
            {vol.Optional("entry_id"): vol.All(cv.ensure_list, [cv.string])}
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OpenTidesConfigEntry) -> bool:
    provider_cls = PROVIDERS.get(entry.data[CONF_PROVIDER])
    if provider_cls is None:
        raise ConfigEntryNotReady(f"unknown provider {entry.data[CONF_PROVIDER]}")
    provider = provider_cls(
        async_get_clientsession(hass), version=integration_version(hass)
    )
    location = location_from_entry(entry)

    coordinator = TideCoordinator(hass, entry, provider, location)
    await coordinator.async_load_capabilities()
    await coordinator.async_setup()

    observed: ObservedCoordinator | None = None
    if coordinator.observed_enabled:
        observed = ObservedCoordinator(hass, entry, provider, location)
        await observed.async_refresh()  # a failure here is not fatal

    entry.runtime_data = OpenTidesData(provider, location, coordinator, observed)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _options_updated(hass: HomeAssistant, entry: OpenTidesConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: OpenTidesConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: OpenTidesConfigEntry) -> None:
    # runtime_data is gone by now (HA clears it on unload); address the store
    # by entry id.
    await remove_store(hass, entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry to the current version.

    Exists from day one so that bumping CONFIG_ENTRY_VERSION later is a code
    change, not a user action. Currently a no-op.
    """
    return True
