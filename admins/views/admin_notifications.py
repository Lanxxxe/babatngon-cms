from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from admins.models import Notification
from core.models import Admin
import sweetify, json




def admin_notification(request):
    """
    Display notifications for admin dashboard - showing only admin notifications.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    # Get filter parameters
    type_filter = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    # Get content type for Admin model
    admin_ct = ContentType.objects.get_for_model(Admin)
    
    # Get only admin notifications
    admin_notifications = Notification.objects.select_related(
        'recipient_content_type', 'sender_content_type',
        'related_complaint', 'related_assistance'
    ).filter(
        recipient_content_type=admin_ct
    ).order_by('-created_at')
    
    # Apply filters
    if type_filter:
        admin_notifications = admin_notifications.filter(notification_type=type_filter)
        
    if status_filter:
        if status_filter == 'unread':
            admin_notifications = admin_notifications.filter(is_read=False)
        elif status_filter == 'read':
            admin_notifications = admin_notifications.filter(is_read=True)
        elif status_filter == 'archived':
            admin_notifications = admin_notifications.filter(is_archived=True)
    
    # Calculate stats (only for admin notifications)
    total_notifications = Notification.objects.filter(recipient_content_type=admin_ct).count()
    pending_cases = Notification.objects.filter(recipient_content_type=admin_ct, is_read=False).count()
    resolved_notifications = Notification.objects.filter(
        recipient_content_type=admin_ct
    ).filter(
        Q(notification_type='case_resolved') | 
        Q(related_complaint__status='resolved') | 
        Q(related_assistance__status='completed')
    ).count()
    urgent_notifications = Notification.objects.filter(
        recipient_content_type=admin_ct, priority='urgent'
    ).count()
    
    # Pagination
    paginator = Paginator(admin_notifications, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get notification types from model choices
    notification_types = [choice[0] for choice in Notification.NOTIFICATION_TYPES]
    
    context = {
        'admin_notifications': page_obj,
        'admin_page_obj': page_obj,
        
        # Stats for cards
        'total_notifications': total_notifications,
        'pending_cases': pending_cases,
        'resolved_notifications': resolved_notifications,
        'urgent_notifications': urgent_notifications,
        
        # Filter options
        'admin_notification_types': notification_types,
        
        # Current filter values
        'current_type': type_filter,
        'current_status': status_filter,
    }
    
    return render(request, 'admin_notification.html', context)


@require_POST
def mark_notification_read(request):
    """
    Mark a specific notification as read.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        notification = Notification.objects.get(id=notification_id)
        notification.mark_as_read()
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def mark_all_notifications_read(request):
    """
    Mark all admin notifications as read.
    """

    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        from django.contrib.contenttypes.models import ContentType
        admin_content_type = ContentType.objects.get_for_model(Admin)
        
        Notification.objects.filter(
            is_read=False,
            recipient_content_type=admin_content_type
        ).update(is_read=True)
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def archive_notification(request):
    """
    Archive a specific notification.
    """

    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        notification = Notification.objects.get(id=notification_id)
        notification.archive()
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def notification_details(request, notification_id):
    """
    Get notification details for modal or page display.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Mark as read when viewed
        if not notification.is_read:
            notification.mark_as_read()
        
        context = {
            'notification': notification,
        }
        
        return render(request, 'notification_details.html', context)
        
    except Notification.DoesNotExist:
        sweetify.error(request, 'Notification not found', timer=3000)
        return redirect('admin_notifications')
    except Exception as e:
        sweetify.error(request, f'Error loading notification: {str(e)}', timer=3000)
        return redirect('admin_notifications')
        return redirect('admin_notifications')

