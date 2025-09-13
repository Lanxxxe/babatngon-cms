def add_notification(request, context):
    """
    Adds a notification for the specified user.
    """
    from .models import Notification  # Import here to avoid circular imports
    user = context.get('current_user')
    message = context.get('notification_message')