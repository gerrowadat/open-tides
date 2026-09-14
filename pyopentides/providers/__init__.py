"""Provider registry.

One module per provider: ``pyopentides/providers/<slug>.py``. Register the
class here so the conformance tests and the HA config flow can find it.
"""

from __future__ import annotations

from pyopentides.provider import TideProvider

# TODO: populate as providers land, e.g.
# from pyopentides.providers.marine_ie import MarineInstituteProvider
PROVIDERS: dict[str, type[TideProvider]] = {}
