from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from core.models import Admin
from admins.models import Notification

def create_status_update_notification(case, case_type, old_status, new_status, staff):
    """
    Create a notification for the complainant when case status is updated.
    """
    try:
        # Get content types
        user_content_type = ContentType.objects.get_for_model(User)
        admin_content_type = ContentType.objects.get_for_model(Admin)
        
        # Create status update message
        status_display = new_status.replace('_', ' ').title()
        old_status_display = old_status.replace('_', ' ').title()
        
        if case_type == 'complaint':
            title = f"Complaint #{case.id} Status Update"
            message = f"Your complaint '{case.title}' status has been updated from '{old_status_display}' to '{status_display}' by staff member {staff.get_full_name()}."
            
            # Determine notification type and priority based on new status
            if new_status == 'resolved':
                notification_type = 'case_resolved'
                priority = 'high'
                message += " Your complaint has been resolved. Please review the resolution details."
            elif new_status == 'closed':
                notification_type = 'case_closed'
                priority = 'normal'
                message += " Your complaint has been closed."
            elif new_status == 'in_progress':
                notification_type = 'status_update'
                priority = 'normal'
                message += " Work is now in progress on your complaint."
            else:
                notification_type = 'status_update'
                priority = 'normal'
        
        else:  # assistance request
            title = f"Assistance Request #{case.id} Status Update"
            message = f"Your assistance request '{case.title}' status has been updated from '{old_status_display}' to '{status_display}' by staff member {staff.get_full_name()}."
            
            # Determine notification type and priority based on new status
            if new_status == 'completed':
                notification_type = 'case_resolved'
                priority = 'high'
                message += " Your assistance request has been completed. Please review the completion details."
            elif new_status == 'approved':
                notification_type = 'request_approved'
                priority = 'high'
                message += " Your assistance request has been approved and will be processed."
            elif new_status == 'rejected':
                notification_type = 'request_rejected'
                priority = 'high'
                message += " Unfortunately, your assistance request has been rejected. Please check the remarks for more details."
            elif new_status == 'in_progress':
                notification_type = 'status_update'
                priority = 'normal'
                message += " Work is now in progress on your assistance request."
            else:
                notification_type = 'status_update'
                priority = 'normal'
        
        # Create the notification
        notification = Notification.objects.create(
            recipient_content_type=user_content_type,
            recipient_object_id=case.user.id,
            sender_content_type=admin_content_type,
            sender_object_id=staff.id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            related_complaint=case if case_type == 'complaint' else None,
            related_assistance=case if case_type == 'assistance' else None,
        )
        
        return notification
        
    except Exception as e:
        # Log error but don't break the status update process
        print(f"Error creating status update notification: {str(e)}")
        return None

def create_remarks_notification(case, case_type, remarks, staff):
    """
    Create a notification for the complainant when staff adds remarks to their case.
    """
    try:
        # Get content types
        user_content_type = ContentType.objects.get_for_model(User)
        admin_content_type = ContentType.objects.get_for_model(Admin)
        
        if case_type == 'complaint':
            title = f"New Remarks on Complaint #{case.id}"
            message = f"Staff member {staff.get_full_name()} has added remarks to your complaint '{case.title}': {remarks}"
        else:  # assistance request
            title = f"New Remarks on Assistance Request #{case.id}"
            message = f"Staff member {staff.get_full_name()} has added remarks to your assistance request '{case.title}': {remarks}"
        
        # Create the notification
        notification = Notification.objects.create(
            recipient_content_type=user_content_type,
            recipient_object_id=case.user.id,
            sender_content_type=admin_content_type,
            sender_object_id=staff.id,
            title=title,
            message=message,
            notification_type='admin_response',
            priority='normal',
            related_complaint=case if case_type == 'complaint' else None,
            related_assistance=case if case_type == 'assistance' else None,
        )
        
        return notification
        
    except Exception as e:
        # Log error but don't break the remarks process
        print(f"Error creating remarks notification: {str(e)}")
        return None

def create_notes_notification(case, case_type, notes, staff):
    """
    Create a notification for the complainant when staff adds resolution/completion notes.
    """
    try:
        # Get content types
        user_content_type = ContentType.objects.get_for_model(User)
        admin_content_type = ContentType.objects.get_for_model(Admin)
        
        if case_type == 'complaint':
            title = f"Resolution Notes Added to Complaint #{case.id}"
            message = f"Resolution notes have been added to your complaint '{case.title}' by staff member {staff.get_full_name()}: {notes}"
            notification_type = 'case_resolved'
        else:  # assistance request
            title = f"Completion Notes Added to Assistance Request #{case.id}"
            message = f"Completion notes have been added to your assistance request '{case.title}' by staff member {staff.get_full_name()}: {notes}"
            notification_type = 'case_resolved'
        
        # Create the notification
        notification = Notification.objects.create(
            recipient_content_type=user_content_type,
            recipient_object_id=case.user.id,
            sender_content_type=admin_content_type,
            sender_object_id=staff.id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority='high',  # High priority since this is usually final resolution
            related_complaint=case if case_type == 'complaint' else None,
            related_assistance=case if case_type == 'assistance' else None,
        )
        
        return notification
        
    except Exception as e:
        # Log error but don't break the notes process
        print(f"Error creating notes notification: {str(e)}")
        return None
