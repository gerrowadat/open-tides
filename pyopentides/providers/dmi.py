"""DMI — Danish Meteorological Institute (Denmark, Greenland, Faroe Islands).

See docs/providers.md#dmi. OGC API Features; predictions in cm relative to
DVR90 (a land datum, so lows are negative).
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any, ClassVar

from pyopentides.exceptions import ProviderUnavailable, StationNotFound
from pyopentides.models import (
    Capabilities,
    Location,
    Observation,
    Point,
    Station,
    TideEvent,
)
from pyopentides.normalise import ensure_utc, normalise_events, normalise_points
from pyopentides.provider import TideProvider


def _t(s: str) -> datetime:
    return ensure_utc(datetime.fromisoformat(s.replace("Z", "+00:00")))


def _interval(start: datetime, end: datetime) -> str:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return f"{ensure_utc(start).strftime(fmt)}/{ensure_utc(end).strftime(fmt)}"


class DmiProvider(TideProvider):
    slug = "dmi"
    name = "DMI (Denmark)"
    attribution = "Tide predictions © Danish Meteorological Institute (DMI), CC BY 4.0"
    licence = "CC-BY-4.0"
    licence_url = "https://creativecommons.org/licenses/by/4.0/"
    datum = "DVR90"
    coordinate_based = False

    # Predictions are computed yearly, two years ahead.
    min_refresh = timedelta(days=7)
    horizon = timedelta(days=90)
    supports_curve = True
    supports_observed = True
    observed_min_refresh = timedelta(minutes=10)

    base_url: ClassVar[str] = "https://opendataapi.dmi.dk/v2/oceanObs/collections"
    obs_parameter: ClassVar[str] = "sealev_dvr"
    # A window of 90 d hilo is ~360 rows; 11 d of 10-min is ~1600. Well under.
    page_limit: ClassVar[str] = "10000"
    _gauge_match_km: ClassVar[float] = 1.0

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._stations: list[Station] | None = None
        self._gauges: list[Station] | None = None

    # -- helpers ---------------------------------------------------------

    async def _items(self, collection: str, **params: str) -> list[dict[str, Any]]:
        text = await self._get(
            f"{self.base_url}/{collection}/items", {"limit": self.page_limit, **params}
        )
        try:
            body = json.loads(text)
        except json.JSONDecodeError as err:
            raise ProviderUnavailable(f"bad JSON from DMI {collection}") from err
        feats = body.get("features")
        if not isinstance(feats, list):
            raise ProviderUnavailable(f"unexpected response from DMI {collection}")
        return [dict(f) for f in feats]

    @staticmethod
    def _station_id(loc: Location) -> str:
        if loc.station_id is None:
            msg = "dmi is station-based"
            raise StationNotFound(msg)
        return loc.station_id

    async def _station(self, station_id: str) -> Station:
        for s in await self.list_stations() or []:
            if s.id == station_id:
                return s
        raise StationNotFound(station_id)

    async def _gauge_for(self, station: Station) -> Station | None:
        """Gauge with sealev_dvr: same id if it exists, else nearest within 1 km."""
        if self._gauges is None:
            feats = await self._items("station")
            self._gauges = []
            for f in feats:
                p = f.get("properties", {})
                if (
                    p.get("status") != "Active"
                    or p.get("validTo") is not None
                    or self.obs_parameter not in (p.get("parameterId") or [])
                ):
                    continue
                lon, lat = f["geometry"]["coordinates"]
                self._gauges.append(
                    Station(
                        id=str(p["stationId"]), name=str(p["name"]), lat=lat, lon=lon
                    )
                )
        for g in self._gauges:
            if g.id == station.id:
                return g
        best = min(self._gauges, key=lambda g: _km(g, station), default=None)
        if best is None or _km(best, station) > self._gauge_match_km:
            return None
        return best

    # -- contract --------------------------------------------------------

    async def list_stations(self) -> list[Station] | None:
        if self._stations is None:
            feats = await self._items("tidewaterstation")
            self._stations = []
            for f in feats:
                p = f.get("properties", {})
                lon, lat = f["geometry"]["coordinates"]
                self._stations.append(
                    Station(
                        id=str(p["stationId"]), name=str(p["name"]), lat=lat, lon=lon
                    )
                )
        return self._stations

    async def capabilities(self, loc: Location) -> Capabilities:
        station = await self._station(self._station_id(loc))
        return Capabilities(
            curve=True, observed=await self._gauge_for(station) is not None
        )

    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        sid = self._station_id(loc)
        feats = await self._items(
            "tidewater",
            stationId=sid,
            predictionType="minimum_maximum",
            datetime=_interval(start, end),
        )
        if not feats:
            await self._station(sid)  # unknown station vs. empty window
        events = [
            TideEvent(
                time=_t(p["predictionTime"]),
                height_m=round(float(p["value"]) / 100, 3),
                kind="high" if p["predictionType"] == "maximum" else "low",
            )
            for f in feats
            if (p := f.get("properties", {})).get("value") is not None
        ]
        return normalise_events(events, start, end)

    async def get_curve(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[Point]:
        sid = self._station_id(loc)
        feats = await self._items(
            "tidewater",
            stationId=sid,
            predictionType="10minutes",
            datetime=_interval(start, end),
        )
        points = [
            Point(
                time=_t(p["predictionTime"]), height_m=round(float(p["value"]) / 100, 3)
            )
            for f in feats
            if (p := f.get("properties", {})).get("value") is not None
        ]
        return normalise_points(points, start, end)

    async def get_observed(self, loc: Location) -> Observation | None:
        station = await self._station(self._station_id(loc))
        gauge = await self._gauge_for(station)
        if gauge is None:
            return None
        feats = await self._items(
            "observation",
            stationId=gauge.id,
            parameterId=self.obs_parameter,
            period="latest-hour",
        )
        rows = [
            (_t(p["observed"]), float(p["value"]))
            for f in feats
            if (p := f.get("properties", {})).get("value") is not None
        ]
        if not rows:
            return None
        t, v = max(rows, key=lambda r: r[0])
        return Observation(time=t, height_m=round(v / 100, 3))


def _km(a: Station, b: Station) -> float:
    x = math.radians(b.lon - a.lon) * math.cos(math.radians((a.lat + b.lat) / 2))
    y = math.radians(b.lat - a.lat)
    return 6371.0 * math.hypot(x, y)
