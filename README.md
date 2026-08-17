## Weather-Based Biking Decision Tool

This project determines whether tomorrow is a good day to bike to work using the OpenWeather One Call 3.0 hourly forecast. It checks rain, snow, and weather alerts, then emails the result.

### Start Here: Configure Your Commute

Before deploying, open **[`config.py`](config.py)** and enter your commute settings. Most users should only need to edit this one file; the weather and email logic in `main.py` can stay unchanged.

The configurable values are:

- ZIP/postal code and country
- time zone
- morning commute hour
- afternoon commute hour
- maximum total rain you are willing to bike in
- start and end of the rain/snow evaluation window
- weather alert keywords that should rule out biking

Default configuration:

```python
# Location
ZIP_CODE = "19067"
COUNTRY_CODE = "US"
TIMEZONE = "America/New_York"

# Representative commute forecast hours (24-hour clock)
MORNING_COMMUTE_HOUR = 7       # 7:00 AM
AFTERNOON_COMMUTE_HOUR = 17    # 5:00 PM

# Maximum total rain allowed during the forecast window
MAX_RAIN_MM = 1.0

# Rain/snow evaluation window
PRECIP_WINDOW_START_HOUR = 21  # 9:00 PM the night before
PRECIP_WINDOW_END_HOUR = 18    # 6:00 PM the day of the ride

# Weather alert event keywords that make the day NOT good for biking
EXTREME_HAZARDS = [
    "Flood",
    "Ice",
    "Air Quality",
    "AIQ",
    "Air",
    "Wind",
    "Tornado",
]
```

The default `EXTREME_HAZARDS` list preserves the project's original checks. OpenWeather alert event names can vary by the national weather-alert provider, so the code checks whether any configured keyword appears in the alert event name.

OpenWeather's alert documentation, including the available standardized severe-weather types, is here:
https://openweathermap.org/openweather-alerts

Time zones use IANA names such as `America/New_York`, `America/Chicago`, `America/Denver`, `America/Los_Angeles`, or `Europe/London`.

A full list of supported time zone names is available here:
https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

Commute and precipitation-window hours use a 24-hour clock from `0` through `23`.

Once [`config.py`](config.py) matches your commute, continue with the OpenWeather, email, and GCP setup below.

### Biking Decision Rules

With the default configuration, a day is considered good for biking when all of the following are true:

- **Rain:** Total forecast rainfall from **9:00 PM the night before through 6:00 PM the day of the ride** is less than **1 mm**.
- **Snow:** No snow is forecast during that same window.
- **Weather alerts:** No alert matching one of the configured `EXTREME_HAZARDS` keywords.

The email also reports representative commute temperatures using the OpenWeather hourly forecast closest to the configured commute hours. The defaults are:

- **Morning commute:** 7:00 AM local time.
- **Afternoon commute:** 5:00 PM local time.

The important change from the original implementation is that these values are selected by their actual local timestamps rather than fixed positions such as `hourly[10]` or `hourly[21]`. Rain and snow are likewise totaled from forecast rows that fall inside the configured time window.

### OpenWeather API Setup

1. Create an OpenWeather account and subscribe to One Call API 3.0.
2. Store the API key in GCP Secret Manager as `weather_api`.
3. The application resolves the configured ZIP/postal code through OpenWeather's ZIP geocoding endpoint and then requests the One Call hourly forecast for those coordinates.

### Email Notifications

Email is sent through Gmail SMTP using an app password. Store the credentials in GCP Secret Manager as:

- `gmail_username`
- `gmail_password`

The email format remains the same and includes:

- ride date
- total rain
- total snow
- weather events
- morning ride feels-like temperature
- afternoon ride feels-like temperature

### Google Cloud Platform Setup

The application runs as a Cloud Run function with the entry point:

`send_weather_email`

A Cloud Build trigger watches the GitHub `main` branch. When code is pushed or merged to `main`, Cloud Build deploys the current repository source to Cloud Run.

Cloud Scheduler should invoke the function in the evening before the ride day. With the default configuration, running it around **9:00 PM America/New_York** works well.

### Notes

OpenWeather One Call hourly `rain.1h` and `snow.1h` values are summed across the configured precipitation window.

Be mindful of OpenWeather API call limits and keep SMTP/API credentials in Secret Manager rather than source control.
