## Weather-Based Biking Decision Tool

This project is a coding solution to determine whether tomorrow is a good day for biking to work based on the weather forecast. The decision is made by considering factors such as rain, snow, air quality, and ice alerts. The OpenWeather API is used to obtain the hourly forecast, and the decision criteria are set to ensure a safe and enjoyable biking experience.

### Biking Decision Rules

The following criteria are used to determine whether it's a good day to bike to work:

- **Rain:** Total rainfall from 9 pm the night before to 6 pm the day of should be less than 1mm.
- **Snow:** No snow is expected in the same time frame.
- **Air Quality:** No air quality alerts.
- **Ice:** No ice alerts.

### OpenWeather API Setup

1. **Create an Account and Subscribe:**
   - Sign up for an account on the [OpenWeather website](https://openweathermap.org/).
   - Subscribe to the OpenWeather API 3.0 and generate an API key.

2. **API Key Usage:**
   - Store the OpenWeather API key securely as it will be used to access weather data.

### Email Notifications Setup (SMTP)

#### Switching to SMTP for Email Notifications

We have moved from using OAuth for email notifications to SMTP due to the expiration of refresh tokens after one week. SMTP provides a less secure but more consistent method for sending emails.

1. **Generate App Password for SMTP:**
   - Visit your email provider's settings page to generate an "App Password" for SMTP access.
   - For detailed instructions on generating an app password, refer to your email provider's documentation. Here is an example guide for [Gmail's App Password setup](https://support.google.com/accounts/answer/185833).

### Google Cloud Platform (GCP) Setup

1. **Create a GCP Account:**
   - [Create a Google Cloud Platform (GCP) Account](https://cloud.google.com/gcp/getting-started)

2. **Setting Up GCP Function:**
   - Follow the [Getting Started with Cloud Functions](https://cloud.google.com/functions/docs/quickstart) guide to create and deploy your Cloud Function.
   - Ensure the Cloud Function has the necessary [IAM and Permissions]([https://cloud.google.com/functions/docs/securing/iam](https://developers.google.com/apps-script/guides/admin/assign-cloud-permissions)) to access external APIs.
   - Set up environment variables, including the OpenWeather API key and SMTP credentials (username and app password).

3. **Scheduling a Function on GCP:**
   - Utilize [Cloud Scheduler](https://cloud.google.com/scheduler/docs/creating) to schedule your Cloud Function to run at 9 am, Monday to Friday.

4. **Store Credentials Locally:**
   - Update the necessary environment variables within your Cloud Function to include the newly generated SMTP credentials for sending emails.

### Conclusion

This project combines weather data from the OpenWeather API, GCP for function execution, and SMTP for email notifications to provide a biking decision tool. Adjust the decision criteria as needed and enjoy biking to work on the best days!

**Note:** Be mindful of API call limits, especially if exceeding the free tier. Set up appropriate safeguards to prevent unwanted charges or account disruptions. Additionally, while SMTP provides consistent access, it's less secure compared to OAuth. Implement necessary precautions to secure your SMTP credentials.
