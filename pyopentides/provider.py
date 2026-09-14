"""The provider contract. See docs/design.md for the rules behind each field."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import ClassVar

from pyopentides.models import Location, Observation, Point, Station, TideEvent


class TideProvider(ABC):
    """Base class every provider subclasses.

    Providers normalise: times tz-aware UTC, heights in metres, events sorted
    and de-duplicated, nothing outside the requested window. Datum is declared,
    never converted.
    """

    # Identity
    slug: ClassVar[str]
    name: ClassVar[str]
    attribution: ClassVar[str]
    licence: ClassVar[str]
    datum: ClassVar[str]
    coordinate_based: ClassVar[bool] = False

    # Politeness — min_refresh is a hard floor the coordinator enforces.
    min_refresh: ClassVar[timedelta]
    horizon: ClassVar[timedelta]
    supports_curve: ClassVar[bool] = False
    supports_observed: ClassVar[bool] = False
    observed_min_refresh: ClassVar[timedelta | None] = None

    async def list_stations(self) -> list[Station] | None:
        """Return the station list, or None if ``coordinate_based``."""
        return None

    @abstractmethod
    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        """Return high/low events in ``[start, end]``, sorted ascending."""

    async def get_curve(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[Point]:
        """Return the height curve in ``[start, end]``. Optional."""
        raise NotImplementedError(f"{self.slug} does not support curves")

    async def get_observed(self, loc: Location) -> Observation | None:
        """Return the latest observed level. Optional."""
        raise NotImplementedError(f"{self.slug} does not support observations")
