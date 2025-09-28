from django.contrib.auth.decorators import user_passes_test
from core.models import Admin
from .models import Admin_Notification


def admin_notifications(request):
    """
    Context processor to provide admin notification count in all admin templates
    """
    context = {}
    
    # Check if user is authenticated and is an admin
    if request.user.is_authenticated:
        try:
            # Get the admin instance for the current user
            admin = Admin.objects.get(user=request.user)
            
            # Get unread notification count for this admin
            unread_count = Admin_Notification.objects.filter(
                recipient=admin,
                is_read=False,
                is_archived=False
            ).count()
            
            context['admin_unread_notifications_count'] = unread_count
            
        except Admin.DoesNotExist:
            # User is not an admin, set count to 0
            context['admin_unread_notifications_count'] = 0
    else:
        context['admin_unread_notifications_count'] = 0
    
    return context