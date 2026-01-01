from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from admins.models import Notification
from core.models import Admin
import sweetify, json
from admins.user_activity_utils import log_activity


# Staff Notification Management
def staff_notifications(request):
    """
    Display all notifications for the current staff member.
    """
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get content type for staff
        staff_content_type = ContentType.objects.get_for_model(Admin)
        
        # Get all notifications for this staff member
        notifications = Notification.objects.filter(
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id
        ).select_related(
            'sender_content_type',
            'related_complaint',
            'related_assistance'
        ).order_by('-created_at')
        
        # Get filter parameters
        current_type = request.GET.get('type', '')
        current_status = request.GET.get('status', '')
        
        # Apply filters
        if current_type:
            notifications = notifications.filter(notification_type=current_type)
        
        if current_status == 'read':
            notifications = notifications.filter(is_read=True)
        elif current_status == 'unread':
            notifications = notifications.filter(is_read=False)
        elif current_status == 'archived':
            notifications = notifications.filter(is_archived=True)
        else:
            # By default, don't show archived notifications
            notifications = notifications.filter(is_archived=False)
        
        # Get unique notification types for filter dropdown
        notification_types = notifications.values_list('notification_type', flat=True).distinct()
        
        # Pagination
        paginator = Paginator(notifications, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Calculate stats
        total_notifications = Notification.objects.filter(
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id,
            is_archived=False
        ).count()
        
        unread_notifications = Notification.objects.filter(
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id,
            is_read=False,
            is_archived=False
        ).count()
        
        urgent_notifications = Notification.objects.filter(
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id,
            priority='urgent',
            is_archived=False
        ).count()
        
        resolved_notifications = total_notifications - unread_notifications
        
        # Log activity
        filter_info = []
        if current_type:
            filter_info.append(f"type: {current_type}")
        if current_status:
            filter_info.append(f"status: {current_status}")
        filter_desc = f" with filters ({', '.join(filter_info)})" if filter_info else ""
        
        log_activity(
            user=current_staff,
            activity_type='notification_viewed',
            activity_category='communication',
            description=f'{current_staff.get_full_name()} accessed notifications{filter_desc}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={
                'total_notifications': total_notifications,
                'unread_count': unread_notifications,
                'urgent_count': urgent_notifications,
                'filters': {'type': current_type, 'status': current_status}
            }
        )
        
        context = {
            'current_staff': current_staff,
            'notifications': page_obj,
            'page_obj': page_obj,
            'notification_types': notification_types,
            'current_type': current_type,
            'current_status': current_status,
            
            # Stats for dashboard cards
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'resolved_notifications': resolved_notifications,
            'urgent_notifications': urgent_notifications,
        }
        
        return render(request, 'staff_notification.html', context)
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    except Exception as e:
        sweetify.error(request, f'Error loading notifications: {str(e)}')
        return redirect('staff_dashboard')


@require_POST
def staff_mark_notification_read(request):
    """
    Mark a specific staff notification as read.
    """
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        # Get content type for staff
        staff_content_type = ContentType.objects.get_for_model(Admin)
        
        # Get the notification and verify it belongs to this staff member
        notification = Notification.objects.get(
            id=notification_id,
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id
        )
        
        notification.mark_as_read()
        
        # Log activity
        log_activity(
            user=current_staff,
            activity_type='notification_read',
            activity_category='communication',
            description=f'{current_staff.get_full_name()} marked notification #{notification_id} as read',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'notification_id': notification_id, 'notification_type': notification.notification_type}
        )
        
        return JsonResponse({'success': True})
        
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Staff not found'})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def staff_mark_all_notifications_read(request):
    """
    Mark all staff notifications as read.
    """
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get content type for staff
        staff_content_type = ContentType.objects.get_for_model(Admin)
        
        # Mark all unread notifications for this staff member as read
        unread_count = Notification.objects.filter(
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id,
            is_read=False
        ).count()
        
        Notification.objects.filter(
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id,
            is_read=False
        ).update(is_read=True)
        
        # Log activity
        log_activity(
            user=current_staff,
            activity_type='notification_read',
            activity_category='communication',
            description=f'{current_staff.get_full_name()} marked all notifications as read',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'notifications_marked': unread_count}
        )
        
        return JsonResponse({'success': True})
        
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Staff not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def staff_archive_notification(request):
    """
    Archive a specific staff notification.
    """
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        # Get content type for staff
        staff_content_type = ContentType.objects.get_for_model(Admin)
        
        # Get the notification and verify it belongs to this staff member
        notification = Notification.objects.get(
            id=notification_id,
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id
        )
        
        notification.archive()
        
        # Log activity
        log_activity(
            user=current_staff,
            activity_type='notification_archived',
            activity_category='communication',
            description=f'{current_staff.get_full_name()} archived notification #{notification_id}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'notification_id': notification_id, 'notification_type': notification.notification_type}
        )
        
        return JsonResponse({'success': True})
        
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Staff not found'})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def staff_notification_details(request, notification_id):
    """
    Get staff notification details for modal or page display.
    """
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get content type for staff
        staff_content_type = ContentType.objects.get_for_model(Admin)
        
        # Get the notification and verify it belongs to this staff member
        notification = Notification.objects.get(
            id=notification_id,
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id
        )
        
        # Mark as read when viewed
        if not notification.is_read:
            notification.mark_as_read()
        
        # Log activity
        log_activity(
            user=current_staff,
            activity_type='notification_viewed',
            activity_category='communication',
            description=f'{current_staff.get_full_name()} viewed notification #{notification_id} details',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={
                'notification_id': notification_id,
                'notification_type': notification.notification_type,
                'priority': notification.priority
            }
        )
        
        context = {
            'notification': notification,
            'current_staff': current_staff,
        }
        
        return render(request, 'staff_notification_details.html', context)
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    except Notification.DoesNotExist:
        sweetify.error(request, 'Notification not found', timer=3000)
        return redirect('staff_notifications')
    except Exception as e:
        sweetify.error(request, f'Error loading notification: {str(e)}', timer=3000)
        return redirect('staff_notifications')
    


























