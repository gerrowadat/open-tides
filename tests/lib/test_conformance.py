"""Conformance tests every registered provider must pass.

Assertions (docs/design.md): events sorted, UTC, metres, within range,
alternating kinds, attribution non-empty, min_refresh >= 1 h.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from pyopentides.providers import PROVIDERS


@pytest.mark.parametrize("provider_cls", PROVIDERS.values(), ids=list(PROVIDERS))
def test_declarations(provider_cls: type) -> None:
    assert provider_cls.slug
    assert provider_cls.name
    assert provider_cls.attribution
    assert provider_cls.licence
    assert provider_cls.licence_url.startswith("https://")
    assert provider_cls.datum
    assert provider_cls.min_refresh >= timedelta(hours=1)
    assert provider_cls.horizon > timedelta(0)
    if provider_cls.supports_observed:
        assert provider_cls.observed_min_refresh is not None


# TODO: get_events conformance against recorded fixtures — sorted, UTC,
# within [start, end], alternating high/low, no duplicates.
