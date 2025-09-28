from django.contrib.contenttypes.models import ContentType
from admins.models import Notification
from core.models import Admin

def staff_notifications_context(request):
    """
    Add staff notification count to context for all staff templates.
    """
    context = {
        'staff_unread_notifications': 0,
    }
    
    # Only add notification context for staff sessions
    staff_id = request.session.get('admin_id')
    if staff_id:
        try:
            current_staff = Admin.objects.get(id=staff_id)
            staff_content_type = ContentType.objects.get_for_model(Admin)
            
            # Count unread notifications for this staff member
            unread_count = Notification.objects.filter(
                recipient_content_type=staff_content_type,
                recipient_object_id=current_staff.id,
                is_read=False,
                is_archived=False
            ).count()
            
            context['staff_unread_notifications'] = unread_count
            
        except Admin.DoesNotExist:
            pass
        except Exception:
            pass
    
    return context