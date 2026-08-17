## Weather-Based Biking Decision Tool

This project determines whether tomorrow is a good day to bike to work using the OpenWeather One Call 3.0 forecast. It evaluates precipitation and safety alerts over the period that matters for the next day's commute, then emails the result.

### Biking Decision Rules

A day is considered good for biking when all of the following are true:

- **Rain:** Total forecast rainfall from **9:00 PM the night before through 6:00 PM the day of the ride** is less than **1 mm**.
- **Snow:** No snow is forecast during that same window.
- **Safety alerts:** No relevant weather alert overlapping that window, including ice/freezing conditions, air quality, flooding, strong wind, tornadoes, or thunderstorms.

The email also reports representative commute temperatures using the OpenWeather hourly forecast closest to:

- **Morning commute:** 7:00 AM local time.
- **Afternoon commute:** 5:00 PM local time.

All forecast timestamps are converted explicitly to `America/New_York`. The logic does not depend on fixed positions such as `hourly[10]`, so the results remain correct if the scheduled function runs a few minutes early/late or daylight-saving time changes.

### OpenWeather API Setup

1. Create an OpenWeather account and subscribe to One Call API 3.0.
2. Store the API key in GCP Secret Manager as `weather_api`.
3. The application first resolves ZIP code `19067` through OpenWeather's ZIP geocoding endpoint and then requests the One Call hourly forecast for those coordinates.

### Email Notifications

Email is sent through Gmail SMTP using an app password. Store the credentials in GCP Secret Manager as:

- `gmail_username`
- `gmail_password`

### Google Cloud Platform Setup

The application runs as a Cloud Run function with the entry point:

`send_weather_email`

A Cloud Build trigger watches the GitHub `main` branch. When code is pushed or merged to `main`, Cloud Build deploys the current repository source to Cloud Run.

Cloud Scheduler should invoke the function in the evening, around **9:00 PM America/New_York**, so the email evaluates the following day's commute.

### Testing Without Sending Email

The HTTP function supports a dry-run query parameter:

`?dry_run=true`

A dry run executes the same geocoding, forecast, time-window, precipitation, alert, and commute-temperature logic but does not send an email. The response is JSON containing:

- ride date
- exact forecast-window start/end timestamps
- rain and snow totals in mm and inches
- relevant alerts
- morning and afternoon forecast timestamps and feels-like temperatures
- final `GOOD` / `NOT_GOOD` decision
- reasons for a negative decision

This is the preferred way to validate forecast logic directly in GCP after a deployment.

### Notes

OpenWeather One Call hourly `rain.1h` and `snow.1h` precipitation values are reported in millimeters per hour even when temperature units are imperial. Because each forecast record represents one hour, the application sums those hourly values across the decision window to estimate total precipitation.

Be mindful of OpenWeather API call limits and keep SMTP/API credentials in Secret Manager rather than source control.
