"""Kartverket / Norwegian Hydrographic Service. See docs/providers.md#kartverket."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from pyopentides.exceptions import ProviderUnavailable, StationNotFound
from pyopentides.models import Location, Observation, Point, Station, TideEvent
from pyopentides.normalise import ensure_utc, normalise_events, normalise_points
from pyopentides.provider import TideProvider


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s).astimezone(UTC)


def _fmt(dt: datetime) -> str:
    return ensure_utc(dt).strftime("%Y-%m-%dT%H:%M")


class KartverketProvider(TideProvider):
    slug = "kartverket"
    name = "Kartverket (Norway)"
    attribution = (
        "Tidal data © Norwegian Mapping Authority, Hydrographic Service "
        "(Kartverket), CC BY 4.0"
    )
    licence = "CC-BY-4.0"
    licence_url = "https://creativecommons.org/licenses/by/4.0/"
    datum = "CD"
    coordinate_based = True

    min_refresh = timedelta(days=1)
    horizon = timedelta(days=90)
    supports_curve = True
    supports_observed = True
    observed_min_refresh = timedelta(minutes=10)

    base_url: ClassVar[str] = "https://vannstand.kartverket.no/tideapi.php"
    refcode: ClassVar[str] = "cd"

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _coords(loc: Location) -> tuple[str, str]:
        if loc.lat is None or loc.lon is None:
            msg = "kartverket is coordinate-based"
            raise StationNotFound(msg)
        return f"{loc.lat:.6f}", f"{loc.lon:.6f}"

    async def _locationdata(
        self, loc: Location, start: datetime, end: datetime, **params: str
    ) -> ET.Element:
        lat, lon = self._coords(loc)
        query = {
            "tide_request": "locationdata",
            "lat": lat,
            "lon": lon,
            "fromtime": _fmt(start),
            "totime": _fmt(end),
            "refcode": self.refcode,
            "tzone": "0",  # default is UTC+1; never rely on it
            "dst": "0",
            "lang": "en",
            **params,
        }
        text = await self._get(self.base_url, query)
        try:
            root = ET.fromstring(text)
        except ET.ParseError as err:
            raise ProviderUnavailable("bad XML from kartverket") from err
        nodata = root.find(".//nodata")
        if nodata is not None:
            raise StationNotFound(nodata.get("info", "no data for this position"))
        if root.find(".//locationdata") is None:
            raise ProviderUnavailable("unexpected response from kartverket")
        return root

    @staticmethod
    def _levels(root: ET.Element, data_type: str) -> list[tuple[datetime, float, str]]:
        out = []
        for data in root.iter("data"):
            if data.get("type") != data_type:
                continue
            unit = data.get("unit", "cm")
            scale = 0.01 if unit == "cm" else 1.0
            for wl in data.iter("waterlevel"):
                value, time = wl.get("value"), wl.get("time")
                if value is None or time is None:
                    continue
                out.append(
                    (_t(time), round(float(value) * scale, 3), wl.get("flag", ""))
                )
        return out

    # -- contract --------------------------------------------------------

    async def list_stations(self) -> list[Station] | None:
        return None

    async def get_events(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[TideEvent]:
        root = await self._locationdata(loc, start, end, datatype="tab")
        events = [
            TideEvent(time=t, height_m=h, kind="high" if flag == "high" else "low")
            for t, h, flag in self._levels(root, "prediction")
            if flag in ("high", "low")
        ]
        return normalise_events(events, start, end)

    async def get_curve(
        self, loc: Location, start: datetime, end: datetime
    ) -> list[Point]:
        root = await self._locationdata(loc, start, end, datatype="pre", interval="10")
        points = [
            Point(time=t, height_m=h) for t, h, _ in self._levels(root, "prediction")
        ]
        return normalise_points(points, start, end)

    async def get_observed(self, loc: Location) -> Observation | None:
        now = self._now()
        root = await self._locationdata(
            loc, now - timedelta(hours=3), now, datatype="obs", interval="10"
        )
        obs = [x for x in self._levels(root, "observation") if x[2] == "obs"]
        if not obs:
            return None
        t, h, _ = max(obs, key=lambda x: x[0])
        return Observation(time=t, height_m=h)
