"""NOAA CO-OPS (United States). See docs/providers.md#noaa_coops."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import ClassVar

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
    """'2026-09-14 05:12' in GMT (we always request time_zone=gmt)."""
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)


class NoaaCoopsProvider(TideProvider):
    slug = "noaa_coops"
    name = "NOAA CO-OPS"
    attribution = "Tide predictions courtesy of NOAA CO-OPS"
    licence = "public-domain"
    licence_url = "https://www.noaa.gov/information-technology/disclaimer"
    datum = "MLLW"
    coordinate_based = False

    min_refresh = timedelta(days=1)
    horizon = timedelta(days=90)
    supports_curve = True
    supports_observed = True
    observed_min_refresh = timedelta(minutes=10)

    data_url: ClassVar[str] = (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    )
    meta_url: ClassVar[str] = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"
    application: ClassVar[str] = "open_tides"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._stations: list[Station] | None = None
        self._types: dict[str, str] = {}  # id -> "R" (harmonic) | "S" (subordinate)
        self._waterlevel_ids: set[str] | None = None

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _station_id(loc: Location) -> str:
        if loc.station_id is None:
            msg = "noaa_coops is station-based"
            raise StationNotFound(msg)
        return loc.station_id

    async def _data(self, station: str, **params: str) -> list[dict[str, str]]:
        query = {
            "station": station,
            "datum": self.datum,
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
            "application": self.application,
            **params,
        }
        try:
            text = await self._get(self.data_url, query)
        except ProviderUnavailable as err:
            # 400 with a JSON error for an unknown station.
            if err.status == 400 and self._error_message(err.body):
                raise StationNotFound(self._error_message(err.body)) from err
            raise
        try:
            body = json.loads(text)
        except json.JSONDecodeError as err:
            raise ProviderUnavailable(f"bad JSON from {self.data_url}") from err
        if "error" in body:
            msg = str(body["error"].get("message", body["error"]))
            if "station" in msg.lower() or "No Predictions" in msg:
                raise StationNotFound(msg)
            raise ProviderUnavailable(msg)
        rows = body.get("predictions") or body.get("data") or []
        return [dict(r) for r in rows]

    @staticmethod
    def _error_message(body: str) -> str:
        try:
            err = json.loads(body).get("error", {})
        except (json.JSONDecodeError, AttributeError):
            return ""
        return str(err.get("message", "")).strip() if isinstance(err, dict) else ""

    async def _meta(self, station_type: str) -> list[dict[str, object]]:
        text = await self._get(
            f"{self.meta_url}/stations.json",
            {"type": station_type, "units": "metric"},
        )
        try:
            body = json.loads(text)
        except json.JSONDecodeError as err:
            raise ProviderUnavailable("bad JSON from mdapi") from err
        return [dict(s) for s in body.get("stations", [])]

    async def _station_type(self, station_id: str) -> str:
        if station_id not in self._types:
            await self.list_stations()
        if station_id not in self._types:
            raise StationNotFound(station_id)
        return self._types[station_id]

    # -- contract --------------------------------------------------------

    async def list_stations(self) -> list[Station] | None:
        if self._stations is None:
            raw = await self._meta("tidepredictions")
            self._stations = []
            for s in raw:
                sid = str(s["id"])
                self._types[sid] = str(s.get("type") or "R")
                self._stations.append(
                    Station(
                        id=sid,
                        name=str(s["name"]),
                        lat=float(s["lat"]),  # type: ignore[arg-type]
                        lon=float(s["lng"]),  # type: ignore[arg-type]
                    )
                )
        return self._stations

    async def capabilities(self, loc: Location) -> Capabilities:
        sid = self._station_id(loc)
        harmonic = await self._station_type(sid) == "R"
        if self._waterlevel_ids is None:
            self._waterlevel_ids = {
                str(s["id"]) for s in await self._meta("waterlevels")
            }
        return Capabilities(curve=harmonic, observed=sid in self._waterlevel_ids)

    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        sid = self._station_id(loc)
        rows = await self._data(
            sid,
            product="predictions",
            interval="hilo",
            begin_date=ensure_utc(start).strftime("%Y%m%d %H:%M"),
            end_date=ensure_utc(end).strftime("%Y%m%d %H:%M"),
        )
        events = [
            TideEvent(
                time=_t(r["t"]),
                height_m=float(r["v"]),
                kind="high" if r["type"].startswith("H") else "low",
            )
            for r in rows
        ]
        return normalise_events(events, start, end)

    async def get_curve(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[Point]:
        sid = self._station_id(loc)
        rows = await self._data(
            sid,
            product="predictions",
            interval="6",
            begin_date=ensure_utc(start).strftime("%Y%m%d %H:%M"),
            end_date=ensure_utc(end).strftime("%Y%m%d %H:%M"),
        )
        points = [Point(time=_t(r["t"]), height_m=float(r["v"])) for r in rows]
        return normalise_points(points, start, end)

    async def get_observed(self, loc: Location) -> Observation | None:
        sid = self._station_id(loc)
        try:
            rows = await self._data(sid, product="water_level", date="latest")
        except StationNotFound:
            return None
        if not rows or not rows[0].get("v"):
            return None
        return Observation(time=_t(rows[0]["t"]), height_m=float(rows[0]["v"]))
