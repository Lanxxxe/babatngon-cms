from django.contrib.auth.decorators import user_passes_test
from django.contrib.contenttypes.models import ContentType
from core.models import Admin
from .models import Notification


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
            
            # Get content type for Admin model
            admin_ct = ContentType.objects.get_for_model(Admin)
            
            # Get unread notification count for this admin using unified notification system
            unread_count = Notification.objects.filter(
                recipient_content_type=admin_ct,
                recipient_object_id=admin.id,
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