from .models import Notification  # Import here to avoid circular imports
def add_notification(request, context):
    """
    Adds a notification for the specified user.
    """
    user = context.get('current_user')
    message = context.get('notification_message')