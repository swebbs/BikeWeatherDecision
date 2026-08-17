import json
import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import functions_framework
import pytz
import requests

from config import (
    AFTERNOON_COMMUTE_HOUR,
    COUNTRY_CODE,
    MAX_RAIN_MM,
    MORNING_COMMUTE_HOUR,
    PRECIP_WINDOW_END_HOUR,
    PRECIP_WINDOW_START_HOUR,
    TIMEZONE,
    ZIP_CODE,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@functions_framework.http
def send_weather_email(request):
    units_of_measure = "Imperial"
    zip_code = ZIP_CODE
    country_code = COUNTRY_CODE
    timezone = TIMEZONE

    send_email(units_of_measure, zip_code, country_code, timezone)
    return "Weather email sent successfully!"


def get_lat_lon_coordinates(zip_code, country_code):
    """Return latitude and longitude for a ZIP/postal code."""
    api_key = os.environ.get("weather_api")
    base_url = "http://api.openweathermap.org/geo/1.0/zip?"
    url = f"{base_url}zip={zip_code},{country_code}&appid={api_key}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    location_data = response.json()
    return {"lat": location_data["lat"], "lon": location_data["lon"]}


def retrieve_weather_data(units_of_measure, zip_code, country_code):
    location = get_lat_lon_coordinates(zip_code, country_code)
    api_key = os.environ.get("weather_api")
    lat = location["lat"]
    lon = location["lon"]
    base_url = "https://api.openweathermap.org/data/3.0/onecall?"
    url = (
        f"{base_url}lat={lat}&lon={lon}&appid={api_key}"
        f"&units={units_of_measure}"
    )
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def check_for_extreme_events(weather_dict):
    """Check for weather alerts that should rule out biking."""
    alerts = weather_dict.get("alerts", [])
    events = [alert.get("event", "") for alert in alerts]

    hazards = ["Flood", "Ice", "Air Quality", "AIQ", "Air", "Wind", "Tornado"]
    extreme_events = [
        event for event in events if any(hazard in event for hazard in hazards)
    ]
    return {"Events": events, "Extreme_Events": extreme_events}


def forecast_window(timezone):
    """Return the configured precipitation window in local time."""
    timezone_obj = pytz.timezone(timezone)
    now = datetime.now(timezone_obj)
    ride_date = now.date() + timedelta(days=1)

    start = timezone_obj.localize(
        datetime.combine(now.date(), datetime.min.time()).replace(
            hour=PRECIP_WINDOW_START_HOUR
        )
    )
    end = timezone_obj.localize(
        datetime.combine(ride_date, datetime.min.time()).replace(
            hour=PRECIP_WINDOW_END_HOUR
        )
    )
    return start, end, ride_date


def hourly_forecasts_in_window(weather_dict, timezone):
    """Return forecast rows that fall inside the configured local-time window."""
    timezone_obj = pytz.timezone(timezone)
    start, end, _ = forecast_window(timezone)

    return [
        hour
        for hour in weather_dict.get("hourly", [])
        if start
        <= datetime.fromtimestamp(hour["dt"], timezone_obj)
        <= end
    ]


def rain_totals(weather_dict, timezone):
    """Return forecast rain total during the configured time window."""
    rain = 0
    for hour in hourly_forecasts_in_window(weather_dict, timezone):
        rain += hour.get("rain", {}).get("1h", 0)
    return round(rain, 2)


def snow_totals(weather_dict, timezone):
    """Return forecast snow total during the configured time window."""
    snow = 0
    for hour in hourly_forecasts_in_window(weather_dict, timezone):
        snow += hour.get("snow", {}).get("1h", 0)
    return round(snow, 2)


def date_time(timestamp, timezone):
    timezone_obj = pytz.timezone(timezone)
    dt = datetime.fromtimestamp(timestamp, timezone_obj)
    return {"Date": dt.strftime("%Y-%m-%d"), "Time": dt.strftime("%I:%M:%S %p")}


def forecast_for_hour(weather_dict, timezone, target_hour):
    """Return the hourly forecast closest to the configured time tomorrow."""
    timezone_obj = pytz.timezone(timezone)
    _, _, ride_date = forecast_window(timezone)
    target = timezone_obj.localize(
        datetime.combine(ride_date, datetime.min.time()).replace(hour=target_hour)
    )

    return min(
        weather_dict["hourly"],
        key=lambda hour: abs(
            datetime.fromtimestamp(hour["dt"], timezone_obj) - target
        ),
    )


def morning_ride_feels_temp(weather_dict, timezone):
    hour = forecast_for_hour(weather_dict, timezone, MORNING_COMMUTE_HOUR)
    date_and_time = date_time(hour["dt"], timezone)
    return {
        "Time": date_and_time["Time"],
        "Date": date_and_time["Date"],
        "temp": hour["feels_like"],
    }


def afternoon_ride_feels_temp(weather_dict, timezone):
    hour = forecast_for_hour(weather_dict, timezone, AFTERNOON_COMMUTE_HOUR)
    date_and_time = date_time(hour["dt"], timezone)
    return {
        "Time": date_and_time["Time"],
        "Date": date_and_time["Date"],
        "temp": hour["feels_like"],
    }


def good_or_bad_bike_day(units_of_measure, zip_code, country_code, timezone):
    weather_dict = retrieve_weather_data(units_of_measure, zip_code, country_code)
    rain = rain_totals(weather_dict, timezone)
    snow = snow_totals(weather_dict, timezone)
    events = check_for_extreme_events(weather_dict)
    morning = morning_ride_feels_temp(weather_dict, timezone)
    afternoon = afternoon_ride_feels_temp(weather_dict, timezone)

    is_good_day = (
        rain < MAX_RAIN_MM
        and snow == 0
        and len(events["Extreme_Events"]) == 0
    )

    if is_good_day:
        subject = "Tomorrow is a GREAT day to bike to work!"
        closing = "Enjoy the ride!"
    else:
        subject = "Sorry, tomorrow is a NOT a GREAT day to bike to work!"
        closing = "Maybe Tomorrow!"

    body = (
        f"Date of Ride: {morning['Date']}<br />"
        f"Total Rain: {round(rain / 25.4, 3)} inches<br />"
        f"Total Snow: {round(snow / 25.4, 3)} inches<br />"
        f"Events: {events['Events']}<br />"
        f"Morning Ride Temperature: {morning['temp']} F<br />"
        f"Afternoon Ride Temperature: {afternoon['temp']} F<br />"
        f"{closing}"
    )
    return subject, body


def send_email(units_of_measure, zip_code, country_code, timezone):
    gmail_username = os.environ.get("gmail_username")
    gmail_password = os.environ.get("gmail_password")

    subject, body = good_or_bad_bike_day(
        units_of_measure, zip_code, country_code, timezone
    )

    message = MIMEMultipart()
    message["From"] = gmail_username
    message["To"] = gmail_username
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp_server:
        smtp_server.starttls()
        smtp_server.login(gmail_username, gmail_password)
        smtp_server.sendmail(gmail_username, gmail_username, message.as_string())
