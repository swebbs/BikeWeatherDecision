"""User-configurable settings for the bike weather decision tool.

Edit this file to customize the forecast for your own commute.

Time zone values must use an IANA time zone name such as:
- America/New_York
- America/Chicago
- America/Denver
- America/Los_Angeles
- Europe/London

Full list:
https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
"""

# Location
ZIP_CODE = "19067"
COUNTRY_CODE = "US"
TIMEZONE = "America/New_York"

# Representative hourly forecast times for each commute.
# Use 24-hour clock values from 0-23.
MORNING_COMMUTE_HOUR = 7   # 7:00 AM
AFTERNOON_COMMUTE_HOUR = 17  # 5:00 PM

# Maximum total rain allowed during the forecast window, in millimeters.
# The day is considered NOT good for biking when rain is >= this value.
MAX_RAIN_MM = 1.0

# Forecast window used to total rain/snow.
# The start is on the evening before the ride; the end is on the ride day.
# Use 24-hour clock values from 0-23.
PRECIP_WINDOW_START_HOUR = 21  # 9:00 PM the night before
PRECIP_WINDOW_END_HOUR = 18    # 6:00 PM the day of the ride

# Weather alert event keywords that make the day NOT good for biking.
# These preserve the project's original hazard checks exactly.
EXTREME_HAZARDS = [
    "Flood",
    "Ice",
    "Air Quality",
    "AIQ",
    "Air",
    "Wind",
    "Tornado",
]

# OpenWeather alert documentation and available severe-weather types:
# https://openweathermap.org/openweather-alerts
