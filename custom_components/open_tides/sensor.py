"""Sensors. Entity IDs and the `events` attribute shape are a public contract."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from . import tide
from .const import (
    CONF_STATION_NAME,
    CURVE_ATTR_STEP,
    CURVE_ATTR_WINDOW,
    DOMAIN,
    EVENTS_ATTR_WINDOW,
)

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import OpenTidesConfigEntry
    from .coordinator import ObservedCoordinator, TideCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OpenTidesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = entry.runtime_data
    coord = data.coordinator
    entities: list[SensorEntity] = [
        TideStateSensor(coord, entry),
        NextEventSensor(coord, entry, "high"),
        NextEventSensor(coord, entry, "low"),
        NextEventHeightSensor(coord, entry, "high"),
        NextEventHeightSensor(coord, entry, "low"),
    ]
    if coord.curve_enabled:
        entities.append(PredictedHeightSensor(coord, entry))
    if data.observed is not None:
        entities.append(ObservedHeightSensor(data.observed, entry))
        entities.append(SurgeSensor(data.observed, coord, entry))
    async_add_entities(entities)


def _device(entry: OpenTidesConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_STATION_NAME) or entry.title,
        manufacturer=entry.runtime_data.provider.name,
        model="Tide station",
        entry_type=None,
    )


def _entity_id(entry: OpenTidesConfigEntry, key: str) -> str:
    """`sensor.<station>_<key>` is a public contract (design.md). Setting
    entity_id before add makes HA use it as the suggested object id instead
    of the user's naming scheme (which may prefix the area)."""
    name = entry.data.get(CONF_STATION_NAME) or entry.title
    return f"sensor.{slugify(name)}_{key}"


class _Base(CoordinatorEntity["TideCoordinator"], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: TideCoordinator, entry: OpenTidesConfigEntry, key: str
    ) -> None:
        super().__init__(coordinator)
        self.entity_id = _entity_id(entry, key)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_attribution = coordinator.provider.attribution
        self._attr_device_info = _device(entry)

    @property
    def now(self) -> datetime:
        return dt_util.utcnow()


class TideStateSensor(_Base):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options: ClassVar[list[str]] = ["rising", "falling"]

    def __init__(
        self, coordinator: TideCoordinator, entry: OpenTidesConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "tide")
        self._entry = entry

    @property
    def native_value(self) -> str | None:
        return tide.state(self.coordinator.data.events, self.now)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        p = self.coordinator.provider
        data = self.coordinator.data
        attrs: dict[str, Any] = {
            "datum": p.datum,
            "provider": p.slug,
            "station": self._entry.data.get(CONF_STATION_NAME) or self._entry.title,
            "licence": p.licence,
            "licence_url": p.licence_url,
            "events": [
                {"time": e.time.isoformat(), "height": e.height_m, "type": e.kind}
                for e in tide.window(data.events, self.now, EVENTS_ATTR_WINDOW)
            ],
        }
        if self.coordinator.curve_enabled:
            attrs["curve"] = [
                [pt.time.isoformat(), pt.height_m]
                for pt in tide.downsample(
                    data.curve, self.now, CURVE_ATTR_WINDOW, CURVE_ATTR_STEP
                )
            ]
        return attrs


class NextEventSensor(_Base):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self, coordinator: TideCoordinator, entry: OpenTidesConfigEntry, kind: str
    ) -> None:
        super().__init__(coordinator, entry, f"next_{kind}")
        self._kind = kind

    @property
    def native_value(self) -> datetime | None:
        ev = tide.next_of(self.coordinator.data.events, self._kind, self.now)
        return ev.time if ev else None


class _Metres(_Base):
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_suggested_display_precision = 2


class NextEventHeightSensor(_Metres):
    def __init__(
        self, coordinator: TideCoordinator, entry: OpenTidesConfigEntry, kind: str
    ) -> None:
        super().__init__(coordinator, entry, f"next_{kind}_height")
        self._kind = kind

    @property
    def native_value(self) -> float | None:
        ev = tide.next_of(self.coordinator.data.events, self._kind, self.now)
        return ev.height_m if ev else None


class PredictedHeightSensor(_Metres):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: TideCoordinator, entry: OpenTidesConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "predicted_height")

    @property
    def native_value(self) -> float | None:
        d = self.coordinator.data
        h = tide.predicted_at(d.events, d.curve, self.now)
        return round(h, 3) if h is not None else None


class ObservedHeightSensor(CoordinatorEntity["ObservedCoordinator"], SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "observed_height"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: ObservedCoordinator, entry: OpenTidesConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self.entity_id = _entity_id(entry, "observed_height")
        self._attr_unique_id = f"{entry.entry_id}_observed_height"
        self._attr_attribution = coordinator.provider.attribution
        self._attr_device_info = _device(entry)

    @property
    def native_value(self) -> float | None:
        obs = self.coordinator.data
        return obs.height_m if obs else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        obs = self.coordinator.data
        return {"observed_at": obs.time.isoformat()} if obs else {}


class SurgeSensor(ObservedHeightSensor):
    _attr_translation_key = "surge"

    def __init__(
        self,
        coordinator: ObservedCoordinator,
        predictions: TideCoordinator,
        entry: OpenTidesConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_id = _entity_id(entry, "surge")
        self._attr_unique_id = f"{entry.entry_id}_surge"
        self._predictions = predictions

    @property
    def native_value(self) -> float | None:
        obs = self.coordinator.data
        if obs is None or self._predictions.data is None:
            return None
        d = self._predictions.data
        predicted = tide.predicted_at(d.events, d.curve, obs.time)
        return round(obs.height_m - predicted, 3) if predicted is not None else None
