"""Provider registry. One module per provider; register the class here."""

from __future__ import annotations

from pyopentides.provider import TideProvider
from pyopentides.providers.kartverket import KartverketProvider
from pyopentides.providers.marine_ie import MarineInstituteProvider
from pyopentides.providers.noaa_coops import NoaaCoopsProvider

PROVIDERS: dict[str, type[TideProvider]] = {
    p.slug: p for p in (MarineInstituteProvider, NoaaCoopsProvider, KartverketProvider)
}
