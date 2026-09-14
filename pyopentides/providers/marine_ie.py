"""Marine Institute (Ireland) via ERDDAP. See docs/providers.md#marine_ie."""

from __future__ import annotations

import csv
import io
import math
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, ClassVar

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

if TYPE_CHECKING:
    from collections.abc import Iterator


def _rows(text: str) -> Iterator[dict[str, str]]:
    """ERDDAP CSV: header row, units row, then data. Skip the units row."""
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader):
        if i == 0:
            continue
        yield row


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def _fmt(dt: datetime) -> str:
    return ensure_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


class MarineInstituteProvider(TideProvider):
    slug = "marine_ie"
    name = "Marine Institute (Ireland)"
    attribution = "Tide predictions © Marine Institute, Ireland (CC BY 4.0)"
    licence = "CC-BY-4.0"
    licence_url = "https://creativecommons.org/licenses/by/4.0/"
    datum = "LAT"
    coordinate_based = False

    min_refresh = timedelta(days=7)
    horizon = timedelta(days=90)
    supports_curve = True
    supports_observed = True
    observed_min_refresh = timedelta(minutes=30)

    # Dataset IDs have rotated before. Keep them here and nowhere else.
    base_url: ClassVar[str] = "https://erddap.marine.ie/erddap/tabledap"
    ds_prediction: ClassVar[str] = "imiTidePrediction"
    ds_highlow: ClassVar[str] = "IMI_TidePrediction_HighLow"
    ds_observed: ClassVar[str] = "IrishNationalTideGaugeNetwork"

    # Prediction station ids ("Dublin_Port") and gauge ids ("Dublin Port")
    # differ. Match gauges to stations by distance.
    _gauge_match_km: ClassVar[float] = 1.0

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._stations: list[Station] | None = None
        self._gauges: list[Station] | None = None
        self._offsets: dict[str, float] = {}

    # -- helpers ---------------------------------------------------------

    def _url(self, dataset: str, query: str) -> str:
        return f"{self.base_url}/{dataset}.csv?{query}"

    async def _query(self, dataset: str, query: str) -> str:
        try:
            return await self._get(self._url(dataset, query))
        except ProviderUnavailable as err:
            # ERDDAP answers 404 to "no rows" as well as "no dataset".
            if "HTTP 404" in str(err):
                raise StationNotFound(str(err)) from err
            raise

    @staticmethod
    def _station_id(loc: Location) -> str:
        if loc.station_id is None:
            msg = "marine_ie is station-based"
            raise StationNotFound(msg)
        return loc.station_id

    async def _lat_offset(self, station_id: str) -> float:
        """LAT minus OD Malin, constant per station. HighLow is ODM only."""
        if station_id not in self._offsets:
            text = await self._query(
                self.ds_prediction,
                f'time,Water_Level,Water_Level_ODM&stationID="{station_id}"'
                '&orderByMax("time")',
            )
            row = next(_rows(text), None)
            if row is None:
                raise StationNotFound(station_id)
            self._offsets[station_id] = round(
                float(row["Water_Level"]) - float(row["Water_Level_ODM"]), 3
            )
        return self._offsets[station_id]

    async def _gauge_for(self, station: Station) -> Station | None:
        if self._gauges is None:
            text = await self._query(
                self.ds_observed, "station_id,longitude,latitude&distinct()"
            )
            self._gauges = [
                Station(
                    id=r["station_id"],
                    name=r["station_id"],
                    lat=float(r["latitude"]),
                    lon=float(r["longitude"]),
                )
                for r in _rows(text)
                if r["station_id"]
            ]
        best = min(self._gauges, key=lambda g: _km(g, station), default=None)
        if best is None or _km(best, station) > self._gauge_match_km:
            return None
        return best

    async def _station(self, station_id: str) -> Station:
        for s in await self.list_stations() or []:
            if s.id == station_id:
                return s
        raise StationNotFound(station_id)

    # -- contract --------------------------------------------------------

    async def list_stations(self) -> list[Station] | None:
        if self._stations is None:
            text = await self._query(
                self.ds_prediction, "stationID,longitude,latitude&distinct()"
            )
            self._stations = [
                Station(
                    id=r["stationID"],
                    name=r["stationID"].replace("_", " "),
                    lat=float(r["latitude"]),
                    lon=float(r["longitude"]),
                )
                for r in _rows(text)
                if r["stationID"]
            ]
        return self._stations

    async def capabilities(self, loc: Location) -> Capabilities:
        station = await self._station(self._station_id(loc))
        observed = not station.id.endswith("_MODELLED") and (
            await self._gauge_for(station) is not None
        )
        return Capabilities(curve=True, observed=observed)

    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        sid = self._station_id(loc)
        offset = await self._lat_offset(sid)
        text = await self._query(
            self.ds_highlow,
            f'time,tide_time_category,Water_Level_ODMalin&stationID="{sid}"'
            f"&time>={_fmt(start)}&time<={_fmt(end)}",
        )
        events = [
            TideEvent(
                time=_t(r["time"]),
                height_m=round(float(r["Water_Level_ODMalin"]) + offset, 3),
                kind="high" if r["tide_time_category"] == "HIGH" else "low",
            )
            for r in _rows(text)
        ]
        return normalise_events(events, start, end)

    async def get_curve(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[Point]:
        sid = self._station_id(loc)
        text = await self._query(
            self.ds_prediction,
            f'time,Water_Level&stationID="{sid}"&time>={_fmt(start)}&time<={_fmt(end)}',
        )
        points = [
            Point(time=_t(r["time"]), height_m=float(r["Water_Level"]))
            for r in _rows(text)
        ]
        return normalise_points(points, start, end)

    async def get_observed(self, loc: Location) -> Observation | None:
        station = await self._station(self._station_id(loc))
        gauge = await self._gauge_for(station)
        if gauge is None:
            return None
        try:
            text = await self._query(
                self.ds_observed,
                f'time,Water_Level_LAT,QC_Flag&station_id="{gauge.id}"'
                '&time>=now-3days&orderByMax("time")',
            )
        except StationNotFound:
            return None  # no rows in the window
        row = next(_rows(text), None)
        if row is None or not row["Water_Level_LAT"]:
            return None
        return Observation(time=_t(row["time"]), height_m=float(row["Water_Level_LAT"]))


def _km(a: Station, b: Station) -> float:
    """Equirectangular distance; fine for a 1 km match radius."""
    x = math.radians(b.lon - a.lon) * math.cos(math.radians((a.lat + b.lat) / 2))
    y = math.radians(b.lat - a.lat)
    return 6371.0 * math.hypot(x, y)
