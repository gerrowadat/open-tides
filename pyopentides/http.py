"""One GET helper. Sets the User-Agent, maps transport failures to ProviderError.

Not a transport abstraction: providers still own their URLs and parsing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

from pyopentides.exceptions import (
    ProviderRateLimited,
    ProviderUnavailable,
    StationNotFound,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

REPO_URL = "https://github.com/gerrowadat/open-tides"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)


def user_agent(version: str) -> str:
    return f"open_tides/{version} (+{REPO_URL})"


async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    *,
    params: Mapping[str, str] | None = None,
    user_agent: str,
    not_found_is_station: bool = False,
) -> str:
    """GET ``url`` and return the body as text.

    Maps: 429 → ProviderRateLimited; 404 → StationNotFound when
    ``not_found_is_station`` else ProviderUnavailable; other non-2xx and any
    aiohttp/timeout error → ProviderUnavailable.
    """
    try:
        async with session.get(
            url,
            params=params,
            headers={"User-Agent": user_agent},
            timeout=DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status == 429:
                raise ProviderRateLimited(f"{url}: 429")
            if resp.status == 404 and not_found_is_station:
                raise StationNotFound(f"{url}: 404")
            if resp.status >= 400:
                body = await resp.text()
                raise ProviderUnavailable(
                    f"{url}: HTTP {resp.status}", status=resp.status, body=body
                )
            return await resp.text()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise ProviderUnavailable(f"{url}: {err}") from err
