"""Provider error hierarchy. Providers raise these; never aiohttp exceptions."""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for anything a provider can raise."""


class ProviderUnavailable(ProviderError):
    """Upstream is down, timing out, or returned something unparseable."""


class ProviderRateLimited(ProviderError):
    """Upstream told us to back off."""


class StationNotFound(ProviderError):
    """The requested station id (or coordinate) is unknown to the provider."""
