"""pyopentides — tide predictions from official national sources.

Pure-Python client library. No Home Assistant imports here.
"""

from __future__ import annotations

from pyopentides.exceptions import (
    ProviderError,
    ProviderRateLimited,
    ProviderUnavailable,
    StationNotFound,
)
from pyopentides.models import Location, Observation, Point, Station, TideEvent
from pyopentides.provider import TideProvider

__version__ = "0.1.0"

__all__ = [
    "Location",
    "Observation",
    "Point",
    "ProviderError",
    "ProviderRateLimited",
    "ProviderUnavailable",
    "Station",
    "StationNotFound",
    "TideEvent",
    "TideProvider",
    "__version__",
]
