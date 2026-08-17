import json
import logging
import os
import smtplib
from datetime import datetime, time, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import functions_framework
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RAIN_LIMIT_MM = 1.0
WINDOW_START_HOUR = 21
WINDOW_END_HOUR = 18
MORNING_RIDE_HOUR = 7
AFTERNOON_RIDE_HOUR = 17
HAZARD_KEYWORDS = (
    "flood",
    "ice",
    "freezing",
    "air quality",
    "wind",
    "tornado",
    "thunderstorm",
)


@functions_framework.http
def send_weather_email(request):
    units_of_measure = "Imperial"
    zip_code = "19067"
    country_code = "US"
    timezone = "America/New_York"

    report = build_bike_report(
        units_of_measure, zip_code, country_code, timezone
    )

    dry_run = request.args.get("dry_run", "").lower() in {"1", "true", "yes"}
    if not dry_run:
        send_report_email(report)
        report["email_sent"] = True
    else:
        report["email_sent"] = False

    return (
        json.dumps(report, indent=2),
        200,
        {"Content-Type": "application/json"},
    )


def get_required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_lat_lon_coordinates(zip_code, country_code):
    """Return latitude and longitude for a ZIP/postal code."""
    api_key = get_required_env("weather_api")
    response = requests.get(
        "https://api.openweathermap.org/geo/1.0/zip",
        params={"zip": f"{zip_code},{country_code}", "appid": api_key},
        timeout=30,
    )
    response.raise_for_status()
    location_data = response.json()
    return {"lat": location_data["lat"], "lon": location_data["lon"]}


def retrieve_weather_data(units_of_measure, zip_code, country_code):
    """Fetch the 48-hour One Call forecast for the requested ZIP code."""
    location = get_lat_lon_coordinates(zip_code, country_code)
    api_key = get_required_env("weather_api")
    response = requests.get(
        "https://api.openweathermap.org/data/3.0/onecall",
        params={
            "lat": location["lat"],
            "lon": location["lon"],
            "appid": api_key,
            "units": units_of_measure,
            "exclude": "current,minutely,daily",
        },
        timeout=30,
    )
    response.raise_for_status()
    weather_data = response.json()
    weather_data["_location"] = location
    return weather_data


def local_dt(timestamp, timezone):
    return datetime.fromtimestamp(timestamp, ZoneInfo(timezone))


def target_times(timezone, now=None):
    """Return the original project window: 9 PM today through 6 PM tomorrow."""
    tz = ZoneInfo(timezone)
    now = now.astimezone(tz) if now else datetime.now(tz)
    today = now.date()
    ride_date = today + timedelta(days=1)

    start = datetime.combine(today, time(WINDOW_START_HOUR), tzinfo=tz)
    end = datetime.combine(ride_date, time(WINDOW_END_HOUR), tzinfo=tz)
    morning = datetime.combine(ride_date, time(MORNING_RIDE_HOUR), tzinfo=tz)
    afternoon = datetime.combine(
        ride_date, time(AFTERNOON_RIDE_HOUR), tzinfo=tz
    )

    return {
        "ride_date": ride_date,
        "window_start": start,
        "window_end": end,
        "morning_target": morning,
        "afternoon_target": afternoon,
    }


def forecast_hours_in_window(weather_dict, timezone, start, end):
    """Return hourly forecasts whose local timestamp falls in [start, end]."""
    hours = []
    for hour in weather_dict.get("hourly", []):
        dt = local_dt(hour["dt"], timezone)
        if start <= dt <= end:
            hours.append((dt, hour))
    return hours


def precipitation_total(window_hours, kind):
    """Sum hourly rain/snow values over the decision window."""
    return round(
        sum(hour.get(kind, {}).get("1h", 0.0) for _, hour in window_hours),
        2,
    )


def closest_forecast_hour(weather_dict, timezone, target):
    """Return the forecast record closest to a specific local clock time."""
    hours = weather_dict.get("hourly", [])
    if not hours:
        raise RuntimeError("OpenWeather response contained no hourly forecast")

    dt, hour = min(
        ((local_dt(hour["dt"], timezone), hour) for hour in hours),
        key=lambda item: abs(item[0] - target),
    )
    return {
        "time": dt.isoformat(),
        "feels_like": hour["feels_like"],
        "temp": hour["temp"],
        "weather": [
            item.get("description", "") for item in hour.get("weather", [])
        ],
    }


def relevant_alerts(weather_dict, timezone, start, end):
    """Return biking-relevant alerts that overlap the decision window."""
    relevant = []
    all_events = []

    for alert in weather_dict.get("alerts", []):
        event = alert.get("event", "")
        all_events.append(event)
        searchable_text = " ".join(
            [
                event,
                alert.get("description", ""),
                " ".join(alert.get("tags", [])),
            ]
        ).lower()

        is_hazard = any(keyword in searchable_text for keyword in HAZARD_KEYWORDS)
        if not is_hazard:
            continue

        alert_start = (
            local_dt(alert["start"], timezone) if alert.get("start") else start
        )
        alert_end = local_dt(alert["end"], timezone) if alert.get("end") else end
        overlaps_window = alert_start <= end and alert_end >= start

        if overlaps_window:
            relevant.append(
                {
                    "event": event,
                    "start": alert_start.isoformat(),
                    "end": alert_end.isoformat(),
                }
            )

    return {"all_events": all_events, "relevant": relevant}


def build_bike_report(units_of_measure, zip_code, country_code, timezone):
    weather_dict = retrieve_weather_data(
        units_of_measure, zip_code, country_code
    )
    times = target_times(timezone)
    window_hours = forecast_hours_in_window(
        weather_dict,
        timezone,
        times["window_start"],
        times["window_end"],
    )

    if not window_hours:
        raise RuntimeError("No hourly forecasts found in the biking window")

    rain_mm = precipitation_total(window_hours, "rain")
    snow_mm = precipitation_total(window_hours, "snow")
    alerts = relevant_alerts(
        weather_dict,
        timezone,
        times["window_start"],
        times["window_end"],
    )
    morning = closest_forecast_hour(
        weather_dict, timezone, times["morning_target"]
    )
    afternoon = closest_forecast_hour(
        weather_dict, timezone, times["afternoon_target"]
    )

    reasons = []
    if rain_mm >= RAIN_LIMIT_MM:
        reasons.append(
            f"forecast rain is {rain_mm} mm (limit < {RAIN_LIMIT_MM} mm)"
        )
    if snow_mm > 0:
        reasons.append(f"forecast snow is {snow_mm} mm")
    if alerts["relevant"]:
        reasons.append(
            "relevant weather alert(s): "
            + ", ".join(alert["event"] for alert in alerts["relevant"])
        )

    is_good_day = not reasons

    return {
        "zip_code": zip_code,
        "location": weather_dict.get("_location", {}),
        "timezone": timezone,
        "ride_date": times["ride_date"].isoformat(),
        "decision": "GOOD" if is_good_day else "NOT_GOOD",
        "is_good_day": is_good_day,
        "reasons": reasons,
        "window": {
            "start": times["window_start"].isoformat(),
            "end": times["window_end"].isoformat(),
            "hourly_records": len(window_hours),
        },
        "rain_mm": rain_mm,
        "rain_inches": round(rain_mm / 25.4, 3),
        "snow_mm": snow_mm,
        "snow_inches": round(snow_mm / 25.4, 3),
        "alerts": alerts,
        "morning_ride": morning,
        "afternoon_ride": afternoon,
    }


def build_email(report):
    if report["is_good_day"]:
        subject = "Tomorrow is a GREAT day to bike to work!"
        closing = "Enjoy the ride!"
    else:
        subject = "Sorry, tomorrow is NOT a GREAT day to bike to work!"
        closing = "Maybe tomorrow!"

    reason_text = (
        "None" if not report["reasons"] else "; ".join(report["reasons"])
    )
    body = (
        f"Date of Ride: {report['ride_date']}<br />"
        f"Forecast Window: 9:00 PM to 6:00 PM ET<br />"
        f"Total Rain: {report['rain_inches']} inches "
        f"({report['rain_mm']} mm)<br />"
        f"Total Snow: {report['snow_inches']} inches "
        f"({report['snow_mm']} mm)<br />"
        f"Relevant Alerts: "
        f"{[a['event'] for a in report['alerts']['relevant']]}<br />"
        f"Decision Reasons: {reason_text}<br />"
        f"Morning Ride ({report['morning_ride']['time']}): "
        f"{report['morning_ride']['feels_like']} F feels like<br />"
        f"Afternoon Ride ({report['afternoon_ride']['time']}): "
        f"{report['afternoon_ride']['feels_like']} F feels like<br />"
        f"{closing}"
    )
    return subject, body


def send_report_email(report):
    gmail_username = get_required_env("gmail_username")
    gmail_password = get_required_env("gmail_password")
    subject, body = build_email(report)

    message = MIMEMultipart()
    message["From"] = gmail_username
    message["To"] = gmail_username
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp_server:
        smtp_server.starttls()
        smtp_server.login(gmail_username, gmail_password)
        smtp_server.sendmail(
            gmail_username, gmail_username, message.as_string()
        )
