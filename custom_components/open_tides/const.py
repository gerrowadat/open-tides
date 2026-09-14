"""Constants for the Open Tides integration."""

from __future__ import annotations

DOMAIN = "open_tides"
REPO_URL = "https://github.com/gerrowadat/open-tides"

# Config entry keys
CONF_PROVIDER = "provider"
CONF_STATION_ID = "station_id"
CONF_STATION_NAME = "station_name"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"

# Options keys
OPT_REFRESH_INTERVAL = "refresh_interval"
OPT_ENABLE_CURVE = "enable_curve"
OPT_ENABLE_OBSERVED = "enable_observed"

# Versions. Bump with a migration, never without.
CONFIG_ENTRY_VERSION = 1
CONFIG_ENTRY_MINOR_VERSION = 1
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.predictions"
