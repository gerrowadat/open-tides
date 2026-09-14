"""Provider error hierarchy. Providers raise these; never aiohttp exceptions."""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for anything a provider can raise."""


class ProviderUnavailable(ProviderError):
    """Upstream is down, timing out, or returned something unparseable.

    ``status`` and ``body`` are set for HTTP errors so a provider can
    re-classify (e.g. NOAA answers 400 with a JSON error for a bad station).
    """

    def __init__(
        self, message: str, *, status: int | None = None, body: str = ""
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class ProviderRateLimited(ProviderError):
    """Upstream told us to back off."""


class StationNotFound(ProviderError):
    """The requested station id (or coordinate) is unknown to the provider."""
