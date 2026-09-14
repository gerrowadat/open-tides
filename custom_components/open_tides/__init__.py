"""Open Tides — tide predictions from official national sources."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS: list[str] = ["sensor"]

__all__ = ["DOMAIN"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Open Tides from a config entry."""
    # TODO: load Store, build coordinator, forward to platforms.
    raise NotImplementedError


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry to the current version.

    Exists from day one so that bumping CONFIG_ENTRY_VERSION later is a code
    change, not a user action. Currently a no-op.
    """
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # TODO
    raise NotImplementedError
