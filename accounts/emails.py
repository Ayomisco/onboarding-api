from celery import shared_task
import requests
from django.utils import timezone

# Your Plunk API Key
PLUNK_API_KEY = "Bearer sk_cf57ddf4d7b470d469d1cf8c6eabbf66cffb13c6492f4348"
PLUNK_URL = "https://api.useplunk.com/v1/track"


def send_email(event_name, email, data):
    """
    Generic function to send emails via Plunk API.
    """
    headers = {
        "Authorization": PLUNK_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "event": event_name,
        "email": email,
        "subscribed": True,
        "data": data
    }

    try:
        response = requests.post(PLUNK_URL, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Email sent successfully to {email}!")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as err:
        print(f"Error sending email: {err}")


def send_otp_email_task(email, first_name, otp_code):
    """
    Sends an OTP email asynchronously using Celery.
    """
    current_time = timezone.now().strftime("%d-%m-%Y")
    send_email("general_send_otp", email, {
               "timestamp": current_time,   "first_name": first_name, "otp_code": str(otp_code), })



def send_welcome_email_task(email, first_name):
    """
    Sends a welcome email asynchronously using Celery.
    """
    current_time = timezone.now().strftime("%d-%m-%Y")
    send_email("welcome_email", email, {"timestamp": current_time, "first_name": first_name})
