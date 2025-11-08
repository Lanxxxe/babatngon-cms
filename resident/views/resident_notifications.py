from core.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.shortcuts import redirect, get_object_or_404, render
from django.core.paginator import Paginator
from admins.models import Notification
import sweetify


# Notifications View
def notifications(request):
    """Display resident notifications."""
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to view notifications.', timer=3000)
        return redirect('homepage')
 
    notif_type = request.GET.get('type', '')
    notif_status = request.GET.get('status', '')
    page_number = request.GET.get('page', 1)


    user_content_type = ContentType.objects.get_for_model(user)

    notifications  = Notification.objects.filter(
        recipient_content_type=user_content_type,
        recipient_object_id=user.id,
    ).order_by('-created_at')

    if notif_status == '':
        notifications = notifications.filter(is_archived=False)

    # Apply filters
    if notif_type:
        notifications = notifications.filter(notification_type__icontains=notif_type)

    if notif_status:
        if notif_status == 'unread':
            notifications = notifications.filter(is_read=False)
        elif notif_status == 'read':
            notifications = notifications.filter(is_read=True)
        elif notif_status == 'archived':
            notifications = notifications.filter(is_archived=True)

    paginator = Paginator(notifications, 5)  # 5 notifications per page
    page_object = paginator.get_page(page_number)

    notification_types = [types[0] for types in Notification.NOTIFICATION_TYPES]

    context = {
        'notifications': page_object,
        'notification_types': notification_types,
        'current_type': notif_type,
        'current_status': notif_status,
        'page_obj': page_object,
    }

    return render(request, 'resident_notifications.html', context)


def resident_notification_details(request, notification_id):
    """Display details of a specific notification."""
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to view notifications.', timer=3000)
        return redirect('homepage')

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient_content_type=ContentType.objects.get_for_model(user),
        recipient_object_id=user.id
    )

    # Mark as read
    if not notification.is_read:
        notification.is_read = True
        notification.save()

    context = {
        'notification': notification,
    }

    return render(request, 'resident_notification_details.html', context)


def resident_mark_notification_read(request, notification_id):
    """Mark a notification as read."""
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to manage notifications.', timer=3000)
        return redirect('homepage')

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient_content_type=ContentType.objects.get_for_model(user),
        recipient_object_id=user.id
    )

    notification.is_read = True
    notification.save()
    sweetify.success(request, 'Notification marked as read.', timer=2000, persistent=True)
    return redirect('notifications')


def resident_archive_notification(request, notification_id):
    """Archive a notification."""
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to manage notifications.', timer=3000, persistent=True)
        return redirect('homepage')

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient_content_type=ContentType.objects.get_for_model(user),
        recipient_object_id=user.id
    )

    notification.is_archived = True
    notification.save()
    sweetify.success(request, 'Notification archived.', timer=2000, persistent=True)
    return redirect('notifications')
