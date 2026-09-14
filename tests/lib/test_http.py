from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from pyopentides.exceptions import (
    ProviderRateLimited,
    ProviderUnavailable,
    StationNotFound,
)
from pyopentides.http import fetch_text, user_agent

URL = "https://example.invalid/x"
UA = user_agent("1.2.3")


def test_user_agent_format() -> None:
    assert UA.startswith("open_tides/1.2.3 (+https://github.com/")


async def test_sets_user_agent(
    session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    mocked.get(URL, body="ok")
    assert await fetch_text(session, URL, user_agent=UA) == "ok"
    ((_, _), calls), *_ = mocked.requests.items()
    assert calls[0].kwargs["headers"]["User-Agent"] == UA


@pytest.mark.parametrize(
    ("status", "exc", "nf"),
    [
        (429, ProviderRateLimited, False),
        (404, StationNotFound, True),
        (404, ProviderUnavailable, False),
        (500, ProviderUnavailable, False),
        (400, ProviderUnavailable, False),
    ],
)
async def test_status_mapping(
    session: aiohttp.ClientSession,
    mocked: aioresponses,
    status: int,
    exc: type[Exception],
    nf: bool,
) -> None:
    mocked.get(URL, status=status, body="body")
    with pytest.raises(exc) as info:
        await fetch_text(session, URL, user_agent=UA, not_found_is_station=nf)
    if exc is ProviderUnavailable:
        assert info.value.status == status  # type: ignore[attr-defined]
        assert info.value.body == "body"  # type: ignore[attr-defined]


async def test_transport_error(
    session: aiohttp.ClientSession, mocked: aioresponses
) -> None:
    mocked.get(URL, exception=aiohttp.ClientConnectionError("down"))
    with pytest.raises(ProviderUnavailable):
        await fetch_text(session, URL, user_agent=UA)
