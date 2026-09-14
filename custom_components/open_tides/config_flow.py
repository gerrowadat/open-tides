"""Config and options flows. See docs/design.md § Config flow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    LocationSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from pyopentides import ProviderError
from pyopentides.providers import PROVIDERS

from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PROVIDER,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    CONFIG_ENTRY_MINOR_VERSION,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    OPT_ENABLE_CURVE,
    OPT_ENABLE_OBSERVED,
    OPT_REFRESH_HOURS,
)

if TYPE_CHECKING:
    from pyopentides import Station, TideProvider

_LOGGER = logging.getLogger(__name__)


def unique_id(provider: str, station_id: str | None, lat: float, lon: float) -> str:
    return f"{provider}:{station_id or f'{lat:.3f},{lon:.3f}'}"


class OpenTidesConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = CONFIG_ENTRY_VERSION
    MINOR_VERSION = CONFIG_ENTRY_MINOR_VERSION

    def __init__(self) -> None:
        self._provider: type[TideProvider] | None = None
        self._stations: list[Station] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OpenTidesOptionsFlow:
        return OpenTidesOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._provider = PROVIDERS[user_input[CONF_PROVIDER]]
            if self._provider.coordinate_based:
                return await self.async_step_coordinates()
            return await self.async_step_station()
        options = [
            SelectOptionDict(value=slug, label=cls.name)
            for slug, cls in sorted(PROVIDERS.items())
        ]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROVIDER): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._provider is not None
        errors: dict[str, str] = {}
        if not self._stations:
            provider = self._provider(async_get_clientsession(self.hass))
            try:
                self._stations = sorted(
                    await provider.list_stations() or [], key=lambda s: s.name
                )
            except ProviderError as err:
                _LOGGER.warning("%s: station list failed: %s", self._provider.slug, err)
                errors["base"] = "cannot_connect"
        if user_input is not None and not errors:
            station = next(
                s for s in self._stations if s.id == user_input[CONF_STATION_ID]
            )
            await self.async_set_unique_id(
                unique_id(self._provider.slug, station.id, station.lat, station.lon)
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=station.name,
                data={
                    CONF_PROVIDER: self._provider.slug,
                    CONF_STATION_ID: station.id,
                    CONF_STATION_NAME: station.name,
                    CONF_LATITUDE: station.lat,
                    CONF_LONGITUDE: station.lon,
                },
            )
        options = [SelectOptionDict(value=s.id, label=s.name) for s in self._stations]
        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders={"provider": self._provider.name},
        )

    async def async_step_coordinates(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._provider is not None
        if user_input is not None:
            loc = user_input["location"]
            lat, lon = float(loc[CONF_LATITUDE]), float(loc[CONF_LONGITUDE])
            name = user_input.get("name") or f"{lat:.3f}, {lon:.3f}"
            await self.async_set_unique_id(
                unique_id(self._provider.slug, None, lat, lon)
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=name,
                data={
                    CONF_PROVIDER: self._provider.slug,
                    CONF_STATION_ID: None,
                    CONF_STATION_NAME: name,
                    CONF_LATITUDE: lat,
                    CONF_LONGITUDE: lon,
                },
            )
        home = {
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
        }
        return self.async_show_form(
            step_id="coordinates",
            data_schema=vol.Schema(
                {
                    vol.Required("location", default=home): LocationSelector(),
                    vol.Optional("name"): str,
                }
            ),
            description_placeholders={"provider": self._provider.name},
        )


class OpenTidesOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        provider = PROVIDERS[self.config_entry.data[CONF_PROVIDER]]
        floor_hours = provider.min_refresh.total_seconds() / 3600
        errors: dict[str, str] = {}
        if user_input is not None:
            if float(user_input[OPT_REFRESH_HOURS]) < floor_hours:
                errors[OPT_REFRESH_HOURS] = "below_floor"
            else:
                return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    OPT_REFRESH_HOURS, default=opts.get(OPT_REFRESH_HOURS, floor_hours)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=floor_hours,
                        max=24 * 90,
                        step=1,
                        unit_of_measurement="h",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    OPT_ENABLE_CURVE, default=opts.get(OPT_ENABLE_CURVE, False)
                ): BooleanSelector(),
                vol.Required(
                    OPT_ENABLE_OBSERVED, default=opts.get(OPT_ENABLE_OBSERVED, False)
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "provider": provider.name,
                "floor": f"{floor_hours:g}",
                "curve": "yes" if provider.supports_curve else "no",
                "observed": "yes" if provider.supports_observed else "no",
            },
        )
