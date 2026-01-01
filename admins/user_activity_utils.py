"""
Utility functions and constants for User Activity tracking system.
This module contains activity types, categories, and helper functions for logging user activities.
"""

from django.contrib.contenttypes.models import ContentType
    

# Activity Types
ACTIVITY_TYPES = [
    # Authentication
    ('login_success', 'Login Successful'),
    ('login_failed', 'Login Failed'),
    ('logout', 'Logout'),
    ('password_change', 'Password Changed'),
    ('password_reset', 'Password Reset'),
    
    # Complaint Activities
    ('complaint_filed', 'Complaint Filed'),
    ('complaint_updated', 'Complaint Updated'),
    ('complaint_viewed', 'Complaint Viewed'),
    ('complaint_assigned', 'Complaint Assigned'),
    ('complaint_reassigned', 'Complaint Reassigned'),
    ('complaint_status_changed', 'Complaint Status Changed'),
    ('complaint_resolved', 'Complaint Resolved'),
    ('complaint_closed', 'Complaint Closed'),
    ('complaint_deleted', 'Complaint Deleted'),
    
    # Assistance Activities
    ('assistance_filed', 'Assistance Request Filed'),
    ('assistance_updated', 'Assistance Request Updated'),
    ('assistance_viewed', 'Assistance Request Viewed'),
    ('assistance_assigned', 'Assistance Request Assigned'),
    ('assistance_reassigned', 'Assistance Request Reassigned'),
    ('assistance_status_changed', 'Assistance Request Status Changed'),
    ('assistance_resolved', 'Assistance Request Resolved'),
    ('assistance_closed', 'Assistance Request Closed'),
    ('assistance_deleted', 'Assistance Request Deleted'),
    
    # Follow-up & Communication
    ('followup_request', 'Follow-up Request'),
    ('comment_added', 'Comment Added'),
    ('notification_sent', 'Notification Sent'),
    ('notification_read', 'Notification Read'),
    
    # Administrative
    ('user_created', 'User Account Created'),
    ('user_updated', 'User Account Updated'),
    ('user_deleted', 'User Account Deleted'),
    ('user_activated', 'User Account Activated'),
    ('user_deactivated', 'User Account Deactivated'),
    ('role_changed', 'User Role Changed'),
    ('settings_changed', 'Settings Changed'),
    
    # File Management
    ('file_uploaded', 'File Uploaded'),
    ('file_downloaded', 'File Downloaded'),
    ('file_deleted', 'File Deleted'),
    
    # Reports & Analytics
    ('report_generated', 'Report Generated'),
    ('report_viewed', 'Report Viewed'),
    ('analytics_accessed', 'Analytics Accessed'),
    
    # System
    ('system_alert', 'System Alert'),
    ('bulk_action', 'Bulk Action Performed'),
    ('export_data', 'Data Exported'),
    ('import_data', 'Data Imported'),
    ('other', 'Other Activity'),
]

# Activity Categories
ACTIVITY_CATEGORIES = [
    ('authentication', 'Authentication'),
    ('case_management', 'Case Management'),
    ('communication', 'Communication'),
    ('administration', 'Administration'),
    ('file_management', 'File Management'),
    ('reporting', 'Reporting'),
    ('system', 'System'),
]


def log_activity(user, activity_type, description, activity_category='system',
                related_complaint=None, related_assistance=None, is_successful=True,
                error_message=None, ip_address=None, user_agent=None, metadata=None):
    """
    Helper function to easily log user activities
    
    Usage:
        from admins.user_activity_utils import log_activity
        
        log_activity(
            user=request.user,
            activity_type='complaint_filed',
            activity_category='case_management',
            description='User filed a new complaint about road damage',
            related_complaint=complaint_instance,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
    """

    # Lazy import to avoid circular dependency
    from admins.models import UserActivity
    from core.models import User, Admin
    
    # Determine user type
    if isinstance(user, Admin):
        # Admin model has a role field that distinguishes admin from staff
        user_type = user.role  # Will be 'admin' or 'staff'
    elif isinstance(user, User):
        user_type = 'resident'
    else:
        user_type = 'unknown'
    
    # Get user name and email
    user_name = user.get_full_name() if hasattr(user, 'get_full_name') else str(user)
    user_email = getattr(user, 'email', None)
    
    # Get content type
    user_ct = ContentType.objects.get_for_model(user)
    
    return UserActivity.objects.create(
        user_content_type=user_ct,
        user_object_id=user.id,
        activity_type=activity_type,
        activity_category=activity_category,
        description=description,
        user_name=user_name,
        user_type=user_type,
        user_email=user_email,
        related_complaint=related_complaint,
        related_assistance=related_assistance,
        is_successful=is_successful,
        error_message=error_message,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )


def log_login_attempt(user, is_successful, ip_address=None, user_agent=None, error_message=None):
    """
    Log a login attempt (successful or failed)
    
    Usage:
        from admins.user_activity_utils import log_login_attempt
        
        log_login_attempt(
            user=user,
            is_successful=True,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
    """
    activity_type = 'login_success' if is_successful else 'login_failed'
    description = f"{'Successful' if is_successful else 'Failed'} login attempt"
    
    return log_activity(
        user=user,
        activity_type=activity_type,
        activity_category='authentication',
        description=description,
        is_successful=is_successful,
        error_message=error_message,
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_logout(user, ip_address=None, user_agent=None):
    """
    Log a logout
    
    Usage:
        from admins.user_activity_utils import log_logout
        
        log_logout(
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
    """
    return log_activity(
        user=user,
        activity_type='logout',
        activity_category='authentication',
        description='User logged out',
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_case_activity(user, case, activity_type, description, ip_address=None, user_agent=None, metadata=None):
    """
    Log case-related activities (complaints or assistance requests)
    
    Usage:
        from admins.user_activity_utils import log_case_activity
        
        log_case_activity(
            user=request.user,
            case=complaint_instance,
            activity_type='complaint_updated',
            description='User updated complaint status to in_progress',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
    """
    from admins.models import Complaint
    
    is_complaint = isinstance(case, Complaint)
    
    return log_activity(
        user=user,
        activity_type=activity_type,
        activity_category='case_management',
        description=description,
        related_complaint=case if is_complaint else None,
        related_assistance=case if not is_complaint else None,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )
