from django.shortcuts import render
from django.http import JsonResponse
from core.sms_util import send_sms, format_complaint_notification, format_emergency_alert
import logging

logger = logging.getLogger(__name__)

def test_sms(request):
    """Test SMS sending functionality and display response"""
    
    phone_number = "09484119128"
    
    if request.method == 'POST':
        # Get test parameters from form
        test_type = request.POST.get('test_type', 'complaint')
        custom_number = request.POST.get('phone_number', phone_number)
        sender_name = request.POST.get('sender_name', '')
        
        # If sender_name is empty or "default", don't pass it (use Semaphore default)
        if sender_name == 'default' or not sender_name:
            sender_name = None
        
        # Prepare test message based on type
        if test_type == 'emergency':
            test_message = format_emergency_alert(
                f"Emergency Complaint #123 filed by Juan Dela Cruz\n"
                f"Title: Fire Incident at Purok 1\n"
                f"Location: 123 Main Street, Barangay Babatngon\n"
                f"Priority: URGENT"
            )
        else:
            test_message = format_complaint_notification(
                complaint_id=123,
                title="Test Complaint - Broken Streetlight",
                status="New Complaint"
            ) + "\nCategory: Infrastructure\nPriority: MEDIUM"
        
        logger.info(f"Testing SMS send to {custom_number} with sender name '{sender_name}'")
        logger.info(f"Message: {test_message}")
        
        # Send the SMS
        result = send_sms(custom_number, test_message, sender_name=sender_name)
        
        # Log the result
        if result['success']:
            logger.info(f"SMS test successful - Message ID: {result.get('data', {}).get('message_id', 'N/A')}")
        else:
            logger.error(f"SMS test failed: {result['message']}")
        
        # Return response as JSON for AJAX or render context for normal request
        context = {
            'result': result,
            'test_message': test_message,
            'phone_number': custom_number,
            'sender_name': sender_name,
            'test_type': test_type
        }
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse(context)
        
        return render(request, 'test_sms_result.html', context)
    
    # GET request - show the test form
    context = {
        'default_phone': phone_number
    }
    return render(request, 'test_sms.html', context)