# utils.py
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
import logging
import hashlib
import uuid
import uuid
import hashlib
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import paypalrestsdk
logger = logging.getLogger(__name__)





def generate_short_code():
    """Generate unique short code for download links"""
    # Create a unique code using UUID and timestamp
    unique_string = f"{uuid.uuid4().hex}{timezone.now().timestamp()}"
    # Create SHA-256 hash and take first 12 characters
    return hashlib.sha256(unique_string.encode()).hexdigest()[:12]

def calculate_expiry_time():
    """Calculate download link expiry time"""
    hours = settings.DOWNLOAD_SETTINGS.get('LINK_EXPIRY_HOURS', 24)
    return timezone.now() + timedelta(hours=hours)

def validate_ip_address(token, request):
    """Validate if request IP matches stored IP"""
    if not settings.DOWNLOAD_SETTINGS.get('ENABLE_IP_RESTRICTION', True):
        return True
        
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    if ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    return token.user_ip == client_ip


# utils.py
import requests
from django.conf import settings

# utils.py
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_pesapal_auth_token():
    """Get OAuth token from PesaPal."""
    try:
        auth_url = (
            "https://cybqa.pesapal.com/pesapalv3/api/Auth/RequestToken"  # Sandbox
            if settings.PESAPAL_ENVIRONMENT == "sandbox"
            else "https://pay.pesapal.com/v3/api/Auth/RequestToken"  # Live
        )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "consumer_key": settings.PESAPAL_CONSUMER_KEY,
            "consumer_secret": settings.PESAPAL_CONSUMER_SECRET,
        }
        response = requests.post(auth_url, json=payload, headers=headers)

        # Log the response for debugging
        logger.info(f"PesaPal Auth Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            return response.json().get("token")
        else:
            logger.error(f"Failed to get PesaPal OAuth token: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error in get_pesapal_auth_token: {str(e)}")
        return None

# utils.py
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# utils.py
def submit_pesapal_order_request(purchase):
    """Submit order request to PesaPal and return the redirect URL."""
    try:
        # Get PesaPal OAuth token
        token = get_pesapal_auth_token()
        if not token:
            logger.error("Failed to get PesaPal OAuth token")
            return None

        # Prepare the API URL
        api_url = (
            "https://cybqa.pesapal.com/pesapalv3/api/Transactions/SubmitOrderRequest"  # Sandbox
            if settings.PESAPAL_ENVIRONMENT == "sandbox"
            else "https://pay.pesapal.com/v3/api/Transactions/SubmitOrderRequest"  # Live
        )

        # Prepare the payload
        payload = {
            "id": str(purchase.purchase_id),
            "currency": purchase.currency,
            "amount": str(purchase.amount_paid),
            "description": f"Purchase of {purchase.app.title}",
            "callback_url": settings.PESAPAL_CALLBACK_URL,
            "notification_id": settings.PESAPAL_IPN_URL,
            "billing_address": {
                "email_address": purchase.user.email,
            },
        }

        # Make the API request
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        response = requests.post(api_url, json=payload, headers=headers)

        # Log the response for debugging
        logger.info(f"PesaPal Order Request Response: {response.status_code} - {response.text}")

        # Check if the request was successful
        if response.status_code == 200:
            return response.json().get("redirect_url")
        else:
            logger.error(f"PesaPal API request failed: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error in submit_pesapal_order_request: {str(e)}")
        return None

def validate_file_checksum(file_path, expected_checksum):
    """Validate file integrity"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() == expected_checksum


def get_client_ip(request):
    """Retrieve the client IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
