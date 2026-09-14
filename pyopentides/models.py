"""Data model shared by every provider. See docs/design.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

TideKind = Literal["high", "low"]


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Location:
    """Either a station id or a coordinate pair; never both, never neither."""

    station_id: str | None = None
    lat: float | None = None
    lon: float | None = None

    def __post_init__(self) -> None:
        has_station = self.station_id is not None
        has_coords = self.lat is not None and self.lon is not None
        if has_station == has_coords:
            msg = "Location needs exactly one of station_id or (lat, lon)"
            raise ValueError(msg)


@dataclass(frozen=True)
class TideEvent:
    time: datetime  # tz-aware UTC
    height_m: float
    kind: TideKind


@dataclass(frozen=True)
class Capabilities:
    """What a provider can do *for a given location*."""

    curve: bool
    observed: bool


@dataclass(frozen=True)
class Point:
    time: datetime  # tz-aware UTC
    height_m: float


@dataclass(frozen=True)
class Observation:
    time: datetime  # tz-aware UTC
    height_m: float
