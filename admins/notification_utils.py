from django.utils import timezone
from .models import Admin_Notification, Resident_Notification, Complaint, AssistanceRequest
from core.models import Admin, User


def create_admin_notification(recipient, title, message, notification_type='other', 
                             action_type='created', priority='normal', sender=None, 
                             related_complaint=None, related_assistance=None):
    """
    Create a notification for admin/staff members.
    
    Args:
        recipient (Admin): The admin/staff member to receive the notification
        title (str): Notification title
        message (str): Notification message
        notification_type (str): Type of notification (see NOTIFICATION_TYPES)
        action_type (str): Type of action that triggered notification
        priority (str): Priority level of notification
        sender (Admin, optional): Who sent/triggered the notification
        related_complaint (Complaint, optional): Related complaint object
        related_assistance (AssistanceRequest, optional): Related assistance request
        metadata (dict, optional): Additional data
    
    Returns:
        Admin_Notification: Created notification object
    """
    try:
        notification = Admin_Notification.objects.create(
            recipient=recipient,
            sender=sender,
            title=title,
            message=message,
            notification_type=notification_type,
            action_type=action_type,
            priority=priority,
            related_complaint=related_complaint,
            related_assistance=related_assistance,
        )
        return notification
    except Exception as e:
        print(f"Error creating admin notification: {str(e)}")
        return None


def create_resident_notification(recipient, title, message, notification_type='other',
                                action_type='created', priority='normal', sender=None,
                                related_complaint=None, related_assistance=None):
    """
    Create a notification for residents.
    
    Args:
        recipient (User): The resident to receive the notification
        title (str): Notification title
        message (str): Notification message
        notification_type (str): Type of notification (see NOTIFICATION_TYPES)
        action_type (str): Type of action that triggered notification
        priority (str): Priority level of notification
        sender (Admin, optional): Admin who triggered the notification
        related_complaint (Complaint, optional): Related complaint object
        related_assistance (AssistanceRequest, optional): Related assistance request
        metadata (dict, optional): Additional data
    
    Returns:
        Resident_Notification: Created notification object
    """
    try:
        notification = Resident_Notification.objects.create(
            recipient=recipient,
            sender=sender,
            title=title,
            message=message,
            notification_type=notification_type,
            action_type=action_type,
            priority=priority,
            related_complaint=related_complaint,
            related_assistance=related_assistance,

        )
        return notification
    except Exception as e:
        print(f"Error creating resident notification: {str(e)}")
        return None


def notify_case_assignment(case, assigned_staff, assigned_by):
    """
    Notify staff when a case is assigned to them.
    
    Args:
        case: Complaint or AssistanceRequest object
        assigned_staff (Admin): Staff member assigned to the case
        assigned_by (Admin): Admin who made the assignment
    
    Returns:
        Admin_Notification: Created notification object
    """
    case_type = 'complaint' if isinstance(case, Complaint) else 'assistance request'
    case_priority = getattr(case, 'priority', getattr(case, 'urgency', 'normal'))
    
    title = f"New {case_type.title()} Assigned"
    message = f"You have been assigned {case_type} #{case.id}: {case.title}"
    
    # Determine notification priority based on case priority
    notification_priority = 'high' if case_priority in ['high', 'urgent', 'critical'] else 'normal'
    
    kwargs = {
        'recipient': assigned_staff,
        'sender': assigned_by,
        'title': title,
        'message': message,
        'notification_type': 'case_assignment',
        'action_type': 'assigned',
        'priority': notification_priority,
    }
    
    if isinstance(case, Complaint):
        kwargs['related_complaint'] = case
    else:
        kwargs['related_assistance'] = case
    
    return create_admin_notification(**kwargs)


def notify_status_change(case, new_status, changed_by, old_status=None):
    """
    Notify resident when their case status changes.
    
    Args:
        case: Complaint or AssistanceRequest object
        new_status (str): New status of the case
        changed_by (Admin): Staff member who changed the status
        old_status (str, optional): Previous status of the case
    
    Returns:
        Resident_Notification: Created notification object
    """
    case_type = 'complaint' if isinstance(case, Complaint) else 'assistance request'
    
    title = f"{case_type.title()} Status Updated"
    message = f"Your {case_type} #{case.id} status has been updated to: {new_status.replace('_', ' ').title()}"
    
    # Add additional context based on status
    if new_status in ['resolved', 'completed']:
        message += ". Thank you for your patience!"
    elif new_status == 'in_progress':
        message += ". Our team is now working on your request."
    elif new_status == 'closed':
        message += ". This case has been closed."
    
    # Determine notification priority
    notification_priority = 'high' if new_status in ['resolved', 'completed', 'closed', 'rejected'] else 'normal'
    
    kwargs = {
        'recipient': case.user,
        'sender': changed_by,
        'title': title,
        'message': message,
        'notification_type': 'status_update',
        'action_type': 'status_changed',
        'priority': notification_priority,
    }
    
    if isinstance(case, Complaint):
        kwargs['related_complaint'] = case
    else:
        kwargs['related_assistance'] = case
    
    return create_resident_notification(**kwargs)


def notify_new_case_filed(case, admins_to_notify=None):
    """
    Notify admins when a new case is filed by a resident.
    
    Args:
        case: Complaint or AssistanceRequest object
        admins_to_notify (list, optional): List of admins to notify, otherwise notifies all active admins
    
    Returns:
        list: List of created notification objects
    """
    case_type = 'complaint' if isinstance(case, Complaint) else 'assistance request'
    case_priority = getattr(case, 'priority', getattr(case, 'urgency', 'normal'))
    
    if not admins_to_notify:
        # Notify all active admins
        admins_to_notify = Admin.objects.filter(is_active=True, role='admin')
    
    title = f"New {case_type.title()} Filed"
    message = f"A new {case_type} has been filed by {case.user.first_name} {case.user.last_name}: {case.title}"
    
    # Determine notification priority
    notification_priority = 'urgent' if case_priority in ['urgent', 'critical'] else 'high' if case_priority == 'high' else 'normal'
    
    notifications = []
    for admin in admins_to_notify:
        kwargs = {
            'recipient': admin,
            'title': title,
            'message': message,
            'notification_type': f'new_{case_type.replace(" ", "_")}',
            'action_type': 'created',
            'priority': notification_priority,
        }
        
        if isinstance(case, Complaint):
            kwargs['related_complaint'] = case
        else:
            kwargs['related_assistance'] = case
        
        notification = create_admin_notification(**kwargs)
        if notification:
            notifications.append(notification)
    
    return notifications


def notify_case_resolved(case, resolved_by):
    """
    Notify resident when their case is resolved.
    
    Args:
        case: Complaint or AssistanceRequest object
        resolved_by (Admin): Staff member who resolved the case
    
    Returns:
        Resident_Notification: Created notification object
    """
    case_type = 'complaint' if isinstance(case, Complaint) else 'assistance request'
    
    title = f"{case_type.title()} Resolved"
    message = f"Great news! Your {case_type} #{case.id} has been resolved. Thank you for your patience."
    
    resolution_notes = getattr(case, 'resolution_notes', getattr(case, 'completion_notes', ''))
    if resolution_notes:
        message += f"\n\nResolution details: {resolution_notes}"
    
    kwargs = {
        'recipient': case.user,
        'sender': resolved_by,
        'title': title,
        'message': message,
        'notification_type': 'case_resolved',
        'action_type': 'resolved',
        'priority': 'high',
    }
    
    if isinstance(case, Complaint):
        kwargs['related_complaint'] = case
    else:
        kwargs['related_assistance'] = case
    
    return create_resident_notification(**kwargs)


def notify_urgent_case(case, staff_members=None):
    """
    Send urgent notifications for high-priority cases.
    
    Args:
        case: Complaint or AssistanceRequest object
        staff_members (list, optional): Specific staff to notify, otherwise notifies all active staff
    
    Returns:
        list: List of created notification objects
    """
    case_type = 'complaint' if isinstance(case, Complaint) else 'assistance request'
    case_priority = getattr(case, 'priority', getattr(case, 'urgency', 'normal'))
    
    # Only send urgent notifications for high-priority cases
    if case_priority not in ['urgent', 'critical', 'high']:
        return []
    
    if not staff_members:
        staff_members = Admin.objects.filter(is_active=True)
    
    title = f"URGENT: {case_type.title()} Requires Attention"
    message = f"An urgent {case_type} #{case.id} needs immediate attention: {case.title}"
    
    notifications = []
    for staff in staff_members:
        kwargs = {
            'recipient': staff,
            'title': title,
            'message': message,
            'notification_type': 'urgent_case',
            'action_type': 'escalated',
            'priority': 'urgent',
        }
        
        if isinstance(case, Complaint):
            kwargs['related_complaint'] = case
        else:
            kwargs['related_assistance'] = case
        
        notification = create_admin_notification(**kwargs)
        if notification:
            notifications.append(notification)
    
    return notifications


def notify_case_reassignment(case, new_staff, old_staff, reassigned_by):
    """
    Notify staff when a case is reassigned.
    
    Args:
        case: Complaint or AssistanceRequest object
        new_staff (Admin): Staff member now assigned to the case
        old_staff (Admin): Previous staff member assigned to the case
        reassigned_by (Admin): Admin who made the reassignment
    
    Returns:
        tuple: (notification_to_new_staff, notification_to_old_staff)
    """
    case_type = 'complaint' if isinstance(case, Complaint) else 'assistance request'
    
    # Notify new staff member
    new_staff_title = f"{case_type.title()} Reassigned to You"
    new_staff_message = f"The {case_type} #{case.id} has been reassigned to you: {case.title}"
    
    # Notify old staff member  
    old_staff_title = f"{case_type.title()} Reassigned"
    old_staff_message = f"The {case_type} #{case.id} has been reassigned to {new_staff.get_full_name() if hasattr(new_staff, 'get_full_name') else str(new_staff)}: {case.title}"
    
    # Create notification for new staff
    new_staff_kwargs = {
        'recipient': new_staff,
        'sender': reassigned_by,
        'title': new_staff_title,
        'message': new_staff_message,
        'notification_type': 'case_assignment',
        'action_type': 'reassigned',
        'priority': 'high',
    }
    
    # Create notification for old staff
    old_staff_kwargs = {
        'recipient': old_staff,
        'sender': reassigned_by,
        'title': old_staff_title,
        'message': old_staff_message,
        'notification_type': 'case_assignment',
        'action_type': 'reassigned',
        'priority': 'normal',
    }
    
    if isinstance(case, Complaint):
        new_staff_kwargs['related_complaint'] = case
        old_staff_kwargs['related_complaint'] = case
    else:
        new_staff_kwargs['related_assistance'] = case
        old_staff_kwargs['related_assistance'] = case
    
    notification_new = create_admin_notification(**new_staff_kwargs)
    notification_old = create_admin_notification(**old_staff_kwargs)
    
    return (notification_new, notification_old)


def notify_case_commented(case, commenter, comment_text):
    """
    Notify relevant parties when a comment is added to a case.
    
    Args:
        case: Complaint or AssistanceRequest object
        commenter (Admin): Staff member who added the comment
        comment_text (str): The comment text
    
    Returns:
        list: List of created notification objects
    """
    case_type = 'complaint' if isinstance(case, Complaint) else 'assistance request'
    
    notifications = []
    
    # Notify the case owner (resident)
    resident_title = f"New Comment on Your {case_type.title()}"
    resident_message = f"A comment has been added to your {case_type} #{case.id}: {case.title}"
    
    resident_kwargs = {
        'recipient': case.user,
        'sender': commenter,
        'title': resident_title,
        'message': resident_message,
        'notification_type': 'admin_response',
        'action_type': 'commented',
        'priority': 'normal',
    }
    
    if isinstance(case, Complaint):
        resident_kwargs['related_complaint'] = case
    else:
        resident_kwargs['related_assistance'] = case
    
    resident_notification = create_resident_notification(**resident_kwargs)
    if resident_notification:
        notifications.append(resident_notification)
    
    # Notify assigned staff (if commenter is not the assigned staff)
    if case.assigned_to and case.assigned_to != commenter:
        staff_title = f"New Comment on Assigned {case_type.title()}"
        staff_message = f"A comment has been added to {case_type} #{case.id} assigned to you: {case.title}"
        
        staff_kwargs = {
            'recipient': case.assigned_to,
            'sender': commenter,
            'title': staff_title,
            'message': staff_message,
            'notification_type': 'system_alert',
            'action_type': 'commented',
            'priority': 'normal',
        }
        
        if isinstance(case, Complaint):
            staff_kwargs['related_complaint'] = case
        else:
            staff_kwargs['related_assistance'] = case
        
        staff_notification = create_admin_notification(**staff_kwargs)
        if staff_notification:
            notifications.append(staff_notification)
    
    return notifications


# Helper functions for notification management

def mark_all_as_read(user, notification_type=None):
    """
    Mark all notifications as read for a user.
    
    Args:
        user: Admin or User object
        notification_type (str, optional): Specific notification type to mark as read
    
    Returns:
        int: Number of notifications marked as read
    """
    try:
        if isinstance(user, Admin):
            notifications = Admin_Notification.objects.filter(recipient=user, is_read=False)
        else:
            notifications = Resident_Notification.objects.filter(recipient=user, is_read=False)
        
        if notification_type:
            notifications = notifications.filter(notification_type=notification_type)
        
        count = 0
        for notification in notifications:
            notification.mark_as_read()
            count += 1
        
        return count
    except Exception as e:
        print(f"Error marking notifications as read: {str(e)}")
        return 0


def get_unread_count(user, notification_type=None):
    """
    Get count of unread notifications for a user.
    
    Args:
        user: Admin or User object
        notification_type (str, optional): Specific notification type to count
    
    Returns:
        int: Number of unread notifications
    """
    try:
        if isinstance(user, Admin):
            notifications = Admin_Notification.objects.filter(recipient=user, is_read=False)
        else:
            notifications = Resident_Notification.objects.filter(recipient=user, is_read=False)
        
        if notification_type:
            notifications = notifications.filter(notification_type=notification_type)
        
        return notifications.count()
    except Exception as e:
        print(f"Error getting unread count: {str(e)}")
        return 0


def cleanup_old_notifications(days=30):
    """
    Archive old notifications to keep the database clean.
    
    Args:
        days (int): Number of days after which to archive notifications
    
    Returns:
        dict: Count of archived notifications
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Archive old admin notifications
        admin_notifications = Admin_Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_archived=False
        )
        admin_count = 0
        for notification in admin_notifications:
            notification.archive()
            admin_count += 1
        
        # Archive old resident notifications
        resident_notifications = Resident_Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_archived=False
        )
        resident_count = 0
        for notification in resident_notifications:
            notification.archive()
            resident_count += 1
        
        return {
            'admin_notifications_archived': admin_count,
            'resident_notifications_archived': resident_count
        }
    except Exception as e:
        print(f"Error cleaning up notifications: {str(e)}")
        return {
            'admin_notifications_archived': 0,
            'resident_notifications_archived': 0
        }
