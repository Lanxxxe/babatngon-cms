import os
import requests
from django.conf import settings
from decouple import config
import logging

logger = logging.getLogger(__name__)

# Semaphore SMS API Configuration
API_ENDPOINT = "https://api.semaphore.co/api/v4/messages"
API_KEY = config('SEMAPHORE_API_KEY', default='')
SENDER_NAME = config('SEMAPHORE_SENDER_NAME', default='BARANGAY')


def is_sms_configured():
    """Check if Semaphore SMS is properly configured"""
    return bool(API_KEY and API_KEY != 'your_semaphore_api_key_here')


# SMS Message Formatting Functions

def format_complaint_notification(complaint_id, title, status):
    """Format message for complaint status update"""
    return (
        f"Barangay CMS Alert:\n"
        f"Complaint #{complaint_id} - {title}\n"
        f"Status: {status.upper()}\n"
        f"Check your account for details."
    )


def format_assistance_notification(assistance_id, title, status):
    """Format message for assistance request update"""
    return (
        f"Barangay CMS Alert:\n"
        f"Assistance #{assistance_id} - {title}\n"
        f"Status: {status.upper()}\n"
        f"Check your account for details."
    )


def format_general_notification(title, message):
    """Format general notification message"""
    return f"Barangay CMS:\n{title}\n{message}"


def format_otp(otp_code):
    """Format OTP verification message"""
    return (
        f"Your Barangay CMS verification code is: {otp_code}\n"
        f"Valid for 10 minutes. Do not share this code."
    )


def format_emergency_alert(message):
    """Format emergency alert message"""
    return f"EMERGENCY ALERT - Barangay CMS:\n{message}"


def send_sms(recipient, message, sender_name=None):
    """
    Send SMS using Semaphore API
    
    Args:
        recipient (str): Phone number of recipient (format: 09171234567 or +639171234567)
        message (str): Message content to send
        sender_name (str, optional): Sender name to display. Defaults to configured sender.
    
    Returns:
        dict: Response with 'success' (bool), 'message' (str), and 'data' (dict if successful)
    
    Example:
        >>> result = send_sms('09171234567', 'Test message')
        >>> if result['success']:
        >>>     print(f"SMS sent! Message ID: {result['data']['message_id']}")
    """
    
    # Check if Semaphore is configured
    if not is_sms_configured():
        logger.warning("Semaphore SMS is not configured. Skipping SMS send.")
        return {
            'success': False,
            'message': 'SMS service not configured',
            'data': None
        }
    
    # Validate recipient
    if not recipient:
        logger.error("SMS send failed: No recipient provided")
        return {
            'success': False,
            'message': 'Recipient phone number is required',
            'data': None
        }
    
    # Clean phone number (remove spaces, dashes)
    recipient = recipient.replace(' ', '').replace('-', '')
    
    # Ensure Philippine format (+63)
    if recipient.startswith('0'):
        recipient = '+63' + recipient[1:]
    elif not recipient.startswith('+63'):
        recipient = '+63' + recipient
    
    # Validate message
    if not message or len(message.strip()) == 0:
        logger.error("SMS send failed: Empty message")
        return {
            'success': False,
            'message': 'Message content is required',
            'data': None
        }
    
    # Prepare request payload
    payload = {
        'apikey': API_KEY,
        'number': recipient,
        'message': message
    }
    
    # Only include sendername if explicitly provided
    # Omitting it allows Semaphore to use the account default
    if sender_name:
        payload['sendername'] = sender_name
    
    try:
        # Send request to Semaphore API
        response = requests.post(
            API_ENDPOINT,
            data=payload,
            timeout=10
        )
        
        # Parse response
        response_data = response.json()
        
        # Handle case where API returns a list instead of dict
        if isinstance(response_data, list):
            # If it's a list, take the first element or convert to dict
            if len(response_data) > 0:
                response_data = response_data[0]
            else:
                response_data = {}
        
        if response.status_code == 200:
            logger.info(f"SMS sent successfully to {recipient}")
            logger.info(f"API Response: {response_data}")
            return {
                'success': True,
                'message': 'SMS sent successfully',
                'data': {
                    'message_id': response_data.get('message_id') if isinstance(response_data, dict) else None,
                    'status': response_data.get('status') if isinstance(response_data, dict) else 'Sent',
                    'recipient': recipient,
                    'raw_response': str(response_data)
                }
            }
        else:
            # Handle different error types
            if isinstance(response_data, dict):
                # Check for sender name error
                if 'senderName' in response_data:
                    error_msg = f"Invalid Sender Name: {response_data['senderName']}. Please use only registered sender names in your Semaphore account, or omit the sender_name parameter to use the default."
                else:
                    error_msg = response_data.get('message', str(response_data))
            else:
                error_msg = str(response_data)
            
            logger.error(f"SMS send failed (HTTP {response.status_code}): {error_msg}")
            logger.error(f"Full response: {response_data}")
            return {
                'success': False,
                'message': f'Failed to send SMS: {error_msg}',
                'data': response_data
            }
            
    except requests.exceptions.Timeout:
        logger.error("SMS send failed: Request timeout")
        return {
            'success': False,
            'message': 'SMS service timeout',
            'data': None
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"SMS send failed: {str(e)}")
        return {
            'success': False,
            'message': f'Network error: {str(e)}',
            'data': None
        }
    except Exception as e:
        logger.error(f"Unexpected error sending SMS: {str(e)}")
        return {
            'success': False,
            'message': f'Unexpected error: {str(e)}',
            'data': None
        }


def send_bulk_sms(recipients, message, sender_name=None):
    """
    Send SMS to multiple recipients
    
    Args:
        recipients (list): List of phone numbers
        message (str): Message content to send
        sender_name (str, optional): Sender name to display
    
    Returns:
        dict: Response with 'success_count', 'failed_count', and 'results' list
    
    Example:
        >>> recipients = ['09171234567', '09187654321']
        >>> result = send_bulk_sms(recipients, 'Bulk message')
        >>> print(f"Sent: {result['success_count']}, Failed: {result['failed_count']}")
    """
    
    results = []
    success_count = 0
    failed_count = 0
    
    for recipient in recipients:
        result = send_sms(recipient, message, sender_name)
        results.append({
            'recipient': recipient,
            'success': result['success'],
            'message': result['message']
        })
        
        if result['success']:
            success_count += 1
        else:
            failed_count += 1
    
    return {
        'success_count': success_count,
        'failed_count': failed_count,
        'total': len(recipients),
        'results': results
    }
