"""Prediction and observation coordinators. See docs/design.md § Politeness."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from pyopentides import (
    Capabilities,
    Location,
    Observation,
    Point,
    ProviderError,
    TideEvent,
)

from .const import (
    BACKFILL,
    CURVE_FETCH_MARGIN,
    DOMAIN,
    JITTER_FRACTION,
    OPT_ENABLE_CURVE,
    OPT_ENABLE_OBSERVED,
    OPT_REFRESH_HOURS,
    STORAGE_KEY,
    STORAGE_VERSION,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from pyopentides import TideProvider

_LOGGER = logging.getLogger(__name__)


@dataclass
class TideData:
    fetched_at: datetime
    start: datetime
    end: datetime
    events: list[TideEvent]
    curve: list[Point]

    def to_store(self) -> dict[str, Any]:
        return {
            "version": STORAGE_VERSION,
            "fetched_at": self.fetched_at.isoformat(),
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "events": [
                {"time": e.time.isoformat(), "height_m": e.height_m, "kind": e.kind}
                for e in self.events
            ],
            "curve": [[p.time.isoformat(), p.height_m] for p in self.curve],
        }

    @classmethod
    def from_store(cls, raw: dict[str, Any]) -> TideData | None:
        """Older or malformed payloads return None: discard and refetch."""
        if raw.get("version") != STORAGE_VERSION:
            return None
        try:
            return cls(
                fetched_at=datetime.fromisoformat(raw["fetched_at"]),
                start=datetime.fromisoformat(raw["start"]),
                end=datetime.fromisoformat(raw["end"]),
                events=[
                    TideEvent(
                        time=datetime.fromisoformat(e["time"]),
                        height_m=float(e["height_m"]),
                        kind=e["kind"],
                    )
                    for e in raw["events"]
                ],
                curve=[
                    Point(time=datetime.fromisoformat(t), height_m=float(h))
                    for t, h in raw.get("curve", [])
                ],
            )
        except (KeyError, TypeError, ValueError):
            return None


def refresh_interval(
    provider: type[TideProvider], options: dict[str, Any]
) -> timedelta:
    """User interval floored at the provider's min_refresh."""
    hours = options.get(OPT_REFRESH_HOURS)
    wanted = timedelta(hours=float(hours)) if hours else provider.min_refresh
    return max(wanted, provider.min_refresh)


class TideCoordinator(DataUpdateCoordinator[TideData]):
    """Fetches predictions. One request per refresh period; store-first startup."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        provider: TideProvider,
        location: Location,
    ) -> None:
        self.provider = provider
        self.location = location
        self.capabilities = Capabilities(curve=False, observed=False)
        self.interval = refresh_interval(type(provider), dict(entry.options))
        jitter = self.interval * random.uniform(0, JITTER_FRACTION)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=self.interval + jitter,
        )
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}"
        )
        self._last_fetch: datetime | None = None

    @property
    def curve_enabled(self) -> bool:
        return bool(self.config_entry.options.get(OPT_ENABLE_CURVE, False)) and (
            self.capabilities.curve
        )

    @property
    def observed_enabled(self) -> bool:
        return bool(self.config_entry.options.get(OPT_ENABLE_OBSERVED, False)) and (
            self.capabilities.observed
        )

    async def async_load_capabilities(self) -> None:
        try:
            self.capabilities = await self.provider.capabilities(self.location)
        except ProviderError as err:
            _LOGGER.warning(
                "%s: capabilities unavailable, assuming none: %s", self.name, err
            )

    async def async_setup(self) -> None:
        """Store first. Fetch only if the cache is missing, stale, or short."""
        raw = await self._store.async_load()
        cached = TideData.from_store(raw) if raw else None
        if cached is not None and self._cache_ok(cached):
            self.async_set_updated_data(cached)
            _LOGGER.debug("%s: using cached predictions to %s", self.name, cached.end)
            return
        await self.async_config_entry_first_refresh()

    def _cache_ok(self, data: TideData) -> bool:
        now = dt_util.utcnow()
        if data.end - now < self.provider.horizon / 2:
            return False
        return not (self.curve_enabled and not data.curve)

    def can_refresh_now(self) -> bool:
        """The refresh service respects the same floor."""
        if self._last_fetch is None:
            return True
        return dt_util.utcnow() - self._last_fetch >= self.provider.min_refresh

    async def _async_update_data(self) -> TideData:
        now = dt_util.utcnow().replace(microsecond=0)
        start, end = now - BACKFILL, now + self.provider.horizon
        try:
            events = await self.provider.get_events(self.location, start, end)
            curve: list[Point] = []
            if self.curve_enabled:
                curve_end = now + self.interval + CURVE_FETCH_MARGIN
                curve = await self.provider.get_curve(self.location, start, curve_end)
        except ProviderError as err:
            raise UpdateFailed(str(err)) from err
        if not events:
            raise UpdateFailed("provider returned no events")
        data = TideData(
            fetched_at=now, start=start, end=end, events=events, curve=curve
        )
        self._last_fetch = now
        await self._store.async_save(data.to_store())
        return data

    async def async_remove_store(self) -> None:
        await self._store.async_remove()


class ObservedCoordinator(DataUpdateCoordinator[Observation | None]):
    """Polls the latest gauge reading at the provider's observed floor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        provider: TideProvider,
        location: Location,
    ) -> None:
        self.provider = provider
        self.location = location
        interval = provider.observed_min_refresh or timedelta(minutes=30)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title} observed",
            update_interval=interval,
        )

    async def _async_update_data(self) -> Observation | None:
        try:
            return await self.provider.get_observed(self.location)
        except ProviderError as err:
            raise UpdateFailed(str(err)) from err
