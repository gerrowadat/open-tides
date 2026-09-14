"""Constants for the Open Tides integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "open_tides"
REPO_URL = "https://github.com/gerrowadat/open-tides"

# Config entry data
CONF_PROVIDER = "provider"
CONF_STATION_ID = "station_id"
CONF_STATION_NAME = "station_name"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"

# Options (every option has a default; old entries must still load)
OPT_REFRESH_HOURS = "refresh_hours"
OPT_ENABLE_CURVE = "enable_curve"
OPT_ENABLE_OBSERVED = "enable_observed"

# Versions. Bump with a migration, never without.
CONFIG_ENTRY_VERSION = 1
CONFIG_ENTRY_MINOR_VERSION = 1
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.predictions"

# Behaviour
JITTER_FRACTION = 0.10
EVENTS_ATTR_WINDOW = timedelta(hours=48)
CURVE_ATTR_WINDOW = timedelta(hours=48)
CURVE_ATTR_STEP = timedelta(minutes=20)
CURVE_FETCH_MARGIN = timedelta(hours=48)
# Observations can lag (Marine Institute ERDDAP: ~30 h); keep predictions
# far enough back that surge can still be computed at the observation time.
BACKFILL = timedelta(days=2)

SERVICE_REFRESH = "refresh"
