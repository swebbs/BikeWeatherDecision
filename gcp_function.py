import functions_framework

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import json
import base64
import functions_framework
#!pip3 install simplegmail
from simplegmail import Gmail
import os
import sys
from typing import List
import json
from datetime import datetime
import logging

#!pip install boto3
import pytz
import requests
import boto3

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import json
from datetime import datetime

import os

from google.cloud import storage
import io
import zipfile
import json

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.cloud import secretmanager

#S3_BUCKET = "running-weather-data"

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@functions_framework.http
def send_weather_email(request):
    # Parameters for the email
    units_of_measure = "Imperial"
    zip_code = '97210'
    country_code = 'US'
    timezone = 'US/Pacific'

    #refresh gmail token if needed
    #refresh_access_token()
    #modify_cloud_file()

    # Call your existing logic to send the weather email
    send_email(units_of_measure, zip_code, country_code, timezone)

    return "Weather email sent successfully!"


def get_lat_lon_coordinates(zip_code,country_code):
    """
    By entering your city name or zipcode and country this returns the lat and lon coordinates
    """
    API_key = os.environ.get('weather_api')
    base_url = "http://api.openweathermap.org/geo/1.0/zip?"
    url = f"{base_url}zip={zip_code},{country_code}&appid={API_key}"
    response = requests.get(url)
    location_data = json.loads(response.text)
    return({'lat':location_data['lat'],"lon":location_data['lon']})

def retrieve_weather_data(units_of_measure: str,zip_code,country_code) -> dict:
    location = get_lat_lon_coordinates(zip_code,country_code)
    api_key = os.environ.get('weather_api')
    lat = location['lat']
    lon =location['lon']
    base_url = "https://api.openweathermap.org/data/3.0/onecall?"
    url = f"{base_url}lat={lat}&lon={lon}&appid={api_key}&units={units_of_measure}"
    response = requests.get(url)
    weather_data = json.loads(response.text)
    return weather_data

def check_for_extreme_events(weather_dict):
  """
  Checks for extreme events that one should avoid biking in. Such as floods, ice, tornados, poor air quality, extreme wind
  """
  try:
    number_of_alerts = len(weather_dict['alerts'])
  except:
    number_of_alerts = 0
  events = []
  todays_events = []
  for i in range(0,number_of_alerts):
    events.append(weather_dict['alerts'][i]['event'])

  hazards = ['Flood', 'Ice', 'Air Quality','AIQ', 'Air', 'Wind', 'Tornado']
  for hazard in hazards:
    for event in events:
      if hazard in event:
        todays_events.append(event)
  return({'Events':events,'Extreme_Events':todays_events})

#gets rain total in mm for 10pm night before to 7pm day of ride. If rain less than 1mm then its good to bike
def rain_totals(weather_dict):
  """
  returns the rain total in mm for 10pm the night before to 7pm the day of
  """

  rain =0
  for i in range(0,21):
    try:
      rain += (weather_dict['hourly'][i]['rain']['1h'])
    except:
      pass
  return(round(rain,2))

def snow_totals(weather_dict):
  """
  returns the snow total in mm for 10pm the night before to 7pm the day of
  """

  snow = 0
  for i in range(0,21):
    try:
      snow += (weather_dict['hourly'][i]['snow']['1h'])
    except:
      pass
  return(round(snow,2))

def date_time(timestamp,timezone):
    """
    Enter time zone like 'US/Pacific', 'US/Eastern' etc for complete list of timezones you may enter view here https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568
    """
    import datetime
    # Create a timezone object
    timezone = pytz.timezone(timezone)
    time = datetime.datetime.fromtimestamp(timestamp,timezone).strftime('%I:%M:%S %p')
    date = datetime.datetime.fromtimestamp(timestamp,timezone).strftime('%Y-%m-%d')
    return({'Date':date,'Time':time})


def morning_ride_feels_temp(weather_dict,timezone):
    """
    Returns the real feel temp(F) for the morning ride 7am-10am, and also returns the timestamp
    """
    morning_ride_feels_temp = weather_dict['hourly'][10]['feels_like']

    import datetime
    # Create a timezone object
    timestamp = weather_dict['hourly'][10]['dt']
    date_and_time = date_time(timestamp,timezone)

    return({'Time':date_and_time['Time'],'Date':date_and_time['Date'],'temp':morning_ride_feels_temp})

def afternoon_ride_feels_temp(weather_dict,timezone):
    """
    Returns the real feel temp(F) for the afternoon ride 4pm-7pm
    """
    afternoon_ride_feels_temp = weather_dict['hourly'][21]['feels_like']


    import datetime
    # Create a timezone object
    timestamp = weather_dict['hourly'][20]['dt']
    date_and_time = date_time(timestamp,timezone)


    return({'Time':date_and_time['Time'],'Date':date_and_time['Date'],'temp':afternoon_ride_feels_temp})

def good_or_bad_bike_day(units_of_measure,zip_code,country_code, timezone):
  """
  This functions set the contents of the email by looking at how much rain is in the forecast
  """

  #Call the weather api and create weather dictionary
  weather_dict = retrieve_weather_data(units_of_measure,zip_code,country_code)
  #calculate the total rain in mm from 10pm night before to 7pm day of
  rain = rain_totals(weather_dict)
  #get the total snow in mm from 10pm the night before to 7pm day of
  snow = snow_totals(weather_dict)
  #now we check for extremem events
  events = check_for_extreme_events(weather_dict)
  #get the morning real feel temp for 7am
  morning = morning_ride_feels_temp(weather_dict,timezone)
  #get the afternoon real feel temp for 4pm
  afternoon = afternoon_ride_feels_temp(weather_dict,timezone)

  if rain < 1 and snow == 0 and len(events['Extreme_Events'])==0:
    subject = "Tomorrow is a GREAT day to bike to work!"
    body = f"Date of Ride: {morning['Date']}<br />\
            Total Rain: {round(rain/25.4,3)} inches<br />\
            Total Snow: {round(snow/25.4,3)} inches<br />\
            Events: {events['Events']}<br />\
            Morning Ride Temperature: {morning['temp']} F<br />\
            Afternoon Ride Temperature: {afternoon['temp']} F<br />\
            Enjoy the ride!"
  elif rain >=1 or snow > 0 or len(events['Extreme_Events'])>0:
    subject = "Sorry, tomorrow is a NOT a GREAT day to bike to work!"
    body = f"Date of Ride: {morning['Date']}<br />\
            Total Rain: {round(rain/25.4,3)} inches<br />\
            Total Snow: {round(snow/25.4,3)} inches<br />\
            Events: {events['Events']}<br />\
            Morning Ride Temperature: {morning['temp']} F<br />\
            Afternoon Ride Temperature: {afternoon['temp']} F<br />\
            Maybe Tomorrow!"
  return(subject,body)

def send_email(units_of_measure,zip_code,country_code, timezone):
  """
  This functions sends the email
  """

  gmail_username = os.environ.get('gmail_username')
  gmail_password = my_variable = os.environ.get('gmail_password')
  subject,body = good_or_bad_bike_day(units_of_measure,zip_code,country_code, timezone)
  sender_email = gmail_username
  password = gmail_password  # Consider using environment variables for security

  recipient_email = gmail_username
  message = MIMEMultipart()
  message['From'] = sender_email
  message['To'] = recipient_email
  message['Subject'] = subject
  message.attach(MIMEText(body, 'html'))

  try:
    smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_server.starttls()
    smtp_server.login(sender_email, password)
    smtp_server.sendmail(sender_email, recipient_email, message.as_string())
    smtp_server.quit()
    return "Email sent successfully!"
  except Exception as e:
    return f"Failed to send email. Error: {e}"
