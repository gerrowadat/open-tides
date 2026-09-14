from __future__ import annotations

from typing import cast

import aiohttp
import pytest

from pyopentides.exceptions import (
    ProviderRateLimited,
    ProviderUnavailable,
    StationNotFound,
)
from pyopentides.http import fetch_text, user_agent

from .fakesession import FakeSession

URL = "https://example.invalid/x"
UA = user_agent("1.2.3")


def test_user_agent_format() -> None:
    assert UA.startswith("open_tides/1.2.3 (+https://github.com/")


async def test_sets_user_agent(
    fake: FakeSession, session: aiohttp.ClientSession
) -> None:
    fake.add(URL, 200, "ok")
    assert await fetch_text(session, URL, user_agent=UA) == "ok"
    assert fake.calls[0].headers["User-Agent"] == UA


async def test_params_are_sent(
    fake: FakeSession, session: aiohttp.ClientSession
) -> None:
    fake.add(URL + "?a=1&b=x", 200, "ok")
    assert await fetch_text(session, URL, params={"a": "1", "b": "x"}, user_agent=UA)


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
    fake: FakeSession,
    session: aiohttp.ClientSession,
    status: int,
    exc: type[Exception],
    nf: bool,
) -> None:
    fake.add(URL, status, "body")
    with pytest.raises(exc) as info:
        await fetch_text(session, URL, user_agent=UA, not_found_is_station=nf)
    if exc is ProviderUnavailable:
        err = cast(ProviderUnavailable, info.value)
        assert err.status == status
        assert err.body == "body"


@pytest.mark.parametrize("exc", [aiohttp.ClientConnectionError("down"), TimeoutError()])
async def test_transport_error(
    fake: FakeSession, session: aiohttp.ClientSession, exc: BaseException
) -> None:
    fake.fail(URL, exc)
    with pytest.raises(ProviderUnavailable):
        await fetch_text(session, URL, user_agent=UA)
