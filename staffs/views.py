from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from admins.models import Complaint, AssistanceRequest, Notification
from core.models import Admin, User
from django.db.models import Count
import sweetify, json

def _create_status_update_notification(case, case_type, old_status, new_status, staff):
    """
    Create a notification for the complainant when case status is updated.
    """
    try:
        # Get content types
        user_content_type = ContentType.objects.get_for_model(User)
        admin_content_type = ContentType.objects.get_for_model(Admin)
        
        # Create status update message
        status_display = new_status.replace('_', ' ').title()
        old_status_display = old_status.replace('_', ' ').title()
        
        if case_type == 'complaint':
            title = f"Complaint #{case.id} Status Update"
            message = f"Your complaint '{case.title}' status has been updated from '{old_status_display}' to '{status_display}' by staff member {staff.get_full_name()}."
            
            # Determine notification type and priority based on new status
            if new_status == 'resolved':
                notification_type = 'case_resolved'
                priority = 'high'
                message += " Your complaint has been resolved. Please review the resolution details."
            elif new_status == 'closed':
                notification_type = 'case_closed'
                priority = 'normal'
                message += " Your complaint has been closed."
            elif new_status == 'in_progress':
                notification_type = 'status_update'
                priority = 'normal'
                message += " Work is now in progress on your complaint."
            else:
                notification_type = 'status_update'
                priority = 'normal'
        
        else:  # assistance request
            title = f"Assistance Request #{case.id} Status Update"
            message = f"Your assistance request '{case.title}' status has been updated from '{old_status_display}' to '{status_display}' by staff member {staff.get_full_name()}."
            
            # Determine notification type and priority based on new status
            if new_status == 'completed':
                notification_type = 'case_resolved'
                priority = 'high'
                message += " Your assistance request has been completed. Please review the completion details."
            elif new_status == 'approved':
                notification_type = 'request_approved'
                priority = 'high'
                message += " Your assistance request has been approved and will be processed."
            elif new_status == 'rejected':
                notification_type = 'request_rejected'
                priority = 'high'
                message += " Unfortunately, your assistance request has been rejected. Please check the remarks for more details."
            elif new_status == 'in_progress':
                notification_type = 'status_update'
                priority = 'normal'
                message += " Work is now in progress on your assistance request."
            else:
                notification_type = 'status_update'
                priority = 'normal'
        
        # Create the notification
        notification = Notification.objects.create(
            recipient_content_type=user_content_type,
            recipient_object_id=case.user.id,
            sender_content_type=admin_content_type,
            sender_object_id=staff.id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            related_complaint=case if case_type == 'complaint' else None,
            related_assistance=case if case_type == 'assistance' else None,
        )
        
        return notification
        
    except Exception as e:
        # Log error but don't break the status update process
        print(f"Error creating status update notification: {str(e)}")
        return None

def _create_remarks_notification(case, case_type, remarks, staff):
    """
    Create a notification for the complainant when staff adds remarks to their case.
    """
    try:
        # Get content types
        user_content_type = ContentType.objects.get_for_model(User)
        admin_content_type = ContentType.objects.get_for_model(Admin)
        
        if case_type == 'complaint':
            title = f"New Remarks on Complaint #{case.id}"
            message = f"Staff member {staff.get_full_name()} has added remarks to your complaint '{case.title}': {remarks}"
        else:  # assistance request
            title = f"New Remarks on Assistance Request #{case.id}"
            message = f"Staff member {staff.get_full_name()} has added remarks to your assistance request '{case.title}': {remarks}"
        
        # Create the notification
        notification = Notification.objects.create(
            recipient_content_type=user_content_type,
            recipient_object_id=case.user.id,
            sender_content_type=admin_content_type,
            sender_object_id=staff.id,
            title=title,
            message=message,
            notification_type='admin_response',
            priority='normal',
            related_complaint=case if case_type == 'complaint' else None,
            related_assistance=case if case_type == 'assistance' else None,
        )
        
        return notification
        
    except Exception as e:
        # Log error but don't break the remarks process
        print(f"Error creating remarks notification: {str(e)}")
        return None

def _create_notes_notification(case, case_type, notes, staff):
    """
    Create a notification for the complainant when staff adds resolution/completion notes.
    """
    try:
        # Get content types
        user_content_type = ContentType.objects.get_for_model(User)
        admin_content_type = ContentType.objects.get_for_model(Admin)
        
        if case_type == 'complaint':
            title = f"Resolution Notes Added to Complaint #{case.id}"
            message = f"Resolution notes have been added to your complaint '{case.title}' by staff member {staff.get_full_name()}: {notes}"
            notification_type = 'case_resolved'
        else:  # assistance request
            title = f"Completion Notes Added to Assistance Request #{case.id}"
            message = f"Completion notes have been added to your assistance request '{case.title}' by staff member {staff.get_full_name()}: {notes}"
            notification_type = 'case_resolved'
        
        # Create the notification
        notification = Notification.objects.create(
            recipient_content_type=user_content_type,
            recipient_object_id=case.user.id,
            sender_content_type=admin_content_type,
            sender_object_id=staff.id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority='high',  # High priority since this is usually final resolution
            related_complaint=case if case_type == 'complaint' else None,
            related_assistance=case if case_type == 'assistance' else None,
        )
        
        return notification
        
    except Exception as e:
        # Log error but don't break the notes process
        print(f"Error creating notes notification: {str(e)}")
        return None

# Create your views here.
def staff_dashboard(request):
    """
    Staff dashboard showing assigned complaints and assistance requests.
    """
    # Get current staff member from session
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        # Redirect to login if no staff session
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get all complaints assigned to current staff member
        assigned_complaints = Complaint.objects.filter(
            assigned_to=current_staff
        ).select_related('user').order_by('-created_at')
        
        # Get all assistance requests assigned to current staff member
        assigned_assistance = AssistanceRequest.objects.filter(
            assigned_to=current_staff
        ).select_related('user').order_by('-created_at')
        
        # Calculate metrics for assigned complaints
        total_complaints = assigned_complaints.count()
        pending_complaints = assigned_complaints.filter(status='pending').count()
        in_progress_complaints = assigned_complaints.filter(status='in_progress').count()
        resolved_complaints = assigned_complaints.filter(status='resolved').count()
        
        # Calculate metrics for assigned assistance requests
        total_assistance = assigned_assistance.count()
        pending_assistance = assigned_assistance.filter(status='pending').count()
        in_progress_assistance = assigned_assistance.filter(status='in_progress').count()
        completed_assistance = assigned_assistance.filter(status='completed').count()
        
        # Get recent assigned complaints (limit to 10 for dashboard display)
        recent_complaints = assigned_complaints[:10]
        
        # Get recent assigned assistance requests (limit to 5)
        recent_assistance = assigned_assistance[:5]
        
        # Get high priority complaints assigned to this staff
        high_priority_complaints = assigned_complaints.filter(
            priority__in=['high', 'urgent']
        ).exclude(status='resolved')[:5]
        
        context = {
            'current_staff': current_staff,
            
            # Complaint metrics
            'total_complaints': total_complaints,
            'pending_complaints': pending_complaints,
            'in_progress_complaints': in_progress_complaints,
            'resolved_complaints': resolved_complaints,
            
            # Assistance metrics
            'assistance_requests': total_assistance,
            'pending_assistance': pending_assistance,
            'in_progress_assistance': in_progress_assistance,
            'completed_assistance': completed_assistance,
            
            # Data for tables/lists
            'recent_complaints': recent_complaints,
            'recent_assistance': recent_assistance,
            'high_priority_complaints': high_priority_complaints,
            
            # For charts - complaint categories
            'assigned_complaints': assigned_complaints,
        }
        
    except Admin.DoesNotExist:
        # If staff not found, redirect to login
        return redirect('admin_login')
    except Exception as e:
        # Fallback with empty data
        context = {
            'total_complaints': 0,
            'pending_complaints': 0,
            'in_progress_complaints': 0,
            'resolved_complaints': 0,
            'assistance_requests': 0,
            'pending_assistance': 0,
            'in_progress_assistance': 0,
            'completed_assistance': 0,
            'recent_complaints': [],
            'recent_assistance': [],
            'high_priority_complaints': [],
            'assigned_complaints': [],
        }

    return render(request, 'staff_dashboard.html', context)


def staff_complaints(request):
    """
    Display all complaints assigned to the current staff member.
    """
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get all complaints assigned to current staff member
        complaints = Complaint.objects.filter(
            assigned_to=current_staff
        ).select_related('user').order_by('-created_at')
        
        # Apply filters if provided
        status_filter = request.GET.get('status')
        priority_filter = request.GET.get('priority')
        
        if status_filter:
            complaints = complaints.filter(status=status_filter)
        
        if priority_filter:
            complaints = complaints.filter(priority=priority_filter)
        
        context = {
            'complaints': complaints,
            'current_staff': current_staff,
            'status_filter': status_filter,
            'priority_filter': priority_filter,
        }
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    
    return render(request, 'staff_complaints.html', context)


def staff_assistance(request):
    """
    Display all assistance requests assigned to the current staff member.
    """
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get all assistance requests assigned to current staff member
        assistance_requests = AssistanceRequest.objects.filter(
            assigned_to=current_staff
        ).select_related('user').order_by('-created_at')
        
        # Apply filters if provided
        status_filter = request.GET.get('status')
        type_filter = request.GET.get('type')
        
        if status_filter:
            assistance_requests = assistance_requests.filter(status=status_filter)
        
        if type_filter:
            assistance_requests = assistance_requests.filter(type=type_filter)
        
        context = {
            'assistance_requests': assistance_requests,
            'current_staff': current_staff,
            'status_filter': status_filter,
            'type_filter': type_filter,
        }
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    
    return render(request, 'staff_assistance.html', context)


def staff_view_case(request, case_type, case_id):
    """
    Display detailed view of a specific complaint or assistance request.
    """
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get the case based on type
        if case_type == 'complaint':
            case = get_object_or_404(
                Complaint.objects.select_related('user', 'assigned_to', 'assigned_by').prefetch_related('attachments'),
                id=case_id,
                assigned_to=current_staff
            )
        elif case_type == 'assistance':
            case = get_object_or_404(
                AssistanceRequest.objects.select_related('user', 'assigned_to').prefetch_related('attachments'),
                id=case_id,
                assigned_to=current_staff
            )
        else:
            sweetify.error(request, 'Invalid case type.', persistent=True, timer=3000)
            return redirect('staff_dashboard')

        print(case.assigned_by)

        context = {
            'case': case,
            'case_type': case_type,
            'current_staff': current_staff,
        }
        
        return render(request, 'staff_view_cases.html', context)
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error loading case details: {str(e)}', persistent=True, timer=3000)
        return redirect('staff_dashboard')


def staff_update_case_status(request, case_type, case_id):
    """
    Update the status of a complaint or assistance request.
    """
    if request.method != 'POST':
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)
    
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        new_status = request.POST.get('status')
        
        if not new_status:
            sweetify.error(request, 'Status is required.')
            return redirect('staff_view_case', case_type=case_type, case_id=case_id)
        
        # Get the case and store old status for comparison
        if case_type == 'complaint':
            case = get_object_or_404(Complaint, id=case_id, assigned_to=current_staff)
            valid_statuses = ['pending', 'in_progress', 'resolved', 'closed']
            
            if new_status not in valid_statuses:
                sweetify.error(request, 'Invalid status for complaint.')
                return redirect('staff_view_case', case_type=case_type, case_id=case_id)
            
            old_status = case.status
            case.status = new_status
            
            # Set resolved_at timestamp if status is resolved
            if new_status == 'resolved' and old_status != 'resolved':
                case.resolved_at = timezone.now()
            
        elif case_type == 'assistance':
            case = get_object_or_404(AssistanceRequest, id=case_id, assigned_to=current_staff)
            valid_statuses = ['pending', 'approved', 'in_progress', 'completed', 'rejected']
            
            if new_status not in valid_statuses:
                sweetify.error(request, 'Invalid status for assistance request.')
                return redirect('staff_view_case', case_type=case_type, case_id=case_id)
            
            old_status = case.status
            case.status = new_status
            
            # Set completed_at timestamp if status is completed
            if new_status == 'completed' and old_status != 'completed':
                case.completed_at = timezone.now()
        
        case.save()
        
        # Create notification for the complainant if status changed
        if old_status != new_status:
            _create_status_update_notification(case, case_type, old_status, new_status, current_staff)
        
        sweetify.success(request, f'{case_type.title()} status updated to {new_status.replace("_", " ").title()} successfully.')
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error updating status: {str(e)}')
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)


def staff_add_remarks(request, case_type, case_id):
    """
    Add admin remarks to a complaint or assistance request.
    """
    if request.method != 'POST':
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)
    
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        remarks = request.POST.get('remarks', '').strip()
        
        if not remarks:
            sweetify.error(request, 'Remarks cannot be empty.')
            return redirect('staff_view_case', case_type=case_type, case_id=case_id)
        
        # Get the case and add remarks
        if case_type == 'complaint':
            case = get_object_or_404(Complaint, id=case_id, assigned_to=current_staff)
        elif case_type == 'assistance':
            case = get_object_or_404(AssistanceRequest, id=case_id, assigned_to=current_staff)
        else:
            sweetify.error(request, 'Invalid case type.')
            return redirect('staff_dashboard')
        
        # Append new remarks to existing remarks with timestamp
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        new_remark = f"[{timestamp}] {current_staff.first_name}: {remarks}"
        
        if case.admin_remarks:
            case.admin_remarks += f"\n\n{new_remark}"
        else:
            case.admin_remarks = new_remark
        
        case.save()
        
        # Create notification for the complainant about new remarks
        _create_remarks_notification(case, case_type, remarks, current_staff)
        
        sweetify.success(request, 'Remarks added successfully.')
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error adding remarks: {str(e)}')
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)


def staff_add_notes(request, case_type, case_id):
    """
    Add resolution/completion notes to a complaint or assistance request.
    """
    if request.method != 'POST':
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)
    
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        notes = request.POST.get('notes', '').strip()
        
        if not notes:
            sweetify.error(request, 'Notes cannot be empty.')
            return redirect('staff_view_case', case_type=case_type, case_id=case_id)
        
        # Get the case and add notes
        if case_type == 'complaint':
            case = get_object_or_404(Complaint, id=case_id, assigned_to=current_staff)
            case.resolution_notes = notes
            note_type = 'Resolution notes'
        elif case_type == 'assistance':
            case = get_object_or_404(AssistanceRequest, id=case_id, assigned_to=current_staff)
            case.completion_notes = notes
            note_type = 'Completion notes'
        else:
            sweetify.error(request, 'Invalid case type.')
            return redirect('staff_dashboard')
        
        case.save()
        
        # Create notification for the complainant about resolution/completion notes
        _create_notes_notification(case, case_type, notes, current_staff)
        
        sweetify.success(request, f'{note_type} updated successfully.')
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error updating notes: {str(e)}')
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)


def staff_profile(request):
    """
    Display staff profile information.
    """
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        context = {
            'current_staff': current_staff,
        }
        
        return render(request, 'staff_profile.html', context)
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error loading profile: {str(e)}')
        return redirect('staff_dashboard')


def staff_update_profile(request):
    """
    Update staff profile information.
    """
    if request.method != 'POST':
        return redirect('staff_profile')
    
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        suffix = request.POST.get('suffix', '').strip()
        email = request.POST.get('email', '').strip()
        department = request.POST.get('department', '').strip()
        position = request.POST.get('position', '').strip()
        
        # Validate required fields
        if not all([first_name, last_name, email, department, position]):
            sweetify.error(request, 'Please fill in all required fields.')
            return redirect('staff_profile')
        
        # Check if email is already taken by another admin
        if Admin.objects.filter(email=email).exclude(id=current_staff.id).exists():
            sweetify.error(request, 'Email address is invalid.')
            return redirect('staff_profile')
        
        # Update staff profile
        current_staff.first_name = first_name
        current_staff.middle_name = middle_name if middle_name else None
        current_staff.last_name = last_name
        current_staff.suffix = suffix if suffix else None
        current_staff.email = email
        current_staff.department = department
        current_staff.position = position
        
        current_staff.save()
        
        sweetify.success(request, 'Profile updated successfully.')
        return redirect('staff_profile')
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error updating profile: {str(e)}')
        return redirect('staff_profile')


def staff_change_password(request):
    """
    Change staff password.
    """
    if request.method != 'POST':
        return redirect('staff_profile')
    
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get form data
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validate inputs
        if not all([current_password, new_password, confirm_password]):
            sweetify.error(request, 'Please fill in all password fields.')
            return redirect('staff_profile')
        
        # Check current password
        if not check_password(current_password, current_staff.password):
            sweetify.error(request, 'Current password is incorrect.')
            return redirect('staff_profile')
        
        # Check if new passwords match
        if new_password != confirm_password:
            sweetify.error(request, 'New passwords do not match.')
            return redirect('staff_profile')
        
        # Validate new password strength
        if len(new_password) < 8:
            sweetify.error(request, 'New password must be at least 8 characters long.')
            return redirect('staff_profile')
        
        # Update password
        current_staff.password = make_password(new_password)
        current_staff.save()
        
        sweetify.success(request, 'Password changed successfully.')
        return redirect('staff_profile')
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error changing password: {str(e)}')
        return redirect('staff_profile')


def staff_update_username(request):
    """
    Update staff username.
    """
    if request.method != 'POST':
        return redirect('staff_profile')
    
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get form data
        new_username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Validate inputs
        if not all([new_username, password]):
            sweetify.error(request, 'Please provide both username and password.')
            return redirect('staff_profile')
        
        # Check current password
        if not check_password(password, current_staff.password):
            sweetify.error(request, 'Password is incorrect.')
            return redirect('staff_profile')
        
        # Check if username is already taken
        if Admin.objects.filter(username=new_username).exclude(id=current_staff.id).exists():
            sweetify.error(request, 'Username is already taken.')
            return redirect('staff_profile')
        
        # Validate username format
        if len(new_username) < 3:
            sweetify.error(request, 'Username must be at least 3 characters long.')
            return redirect('staff_profile')
        
        if not new_username.isalnum():
            sweetify.error(request, 'Username can only contain letters and numbers.')
            return redirect('staff_profile')
        
        # Update username
        current_staff.username = new_username
        current_staff.save()
        
        sweetify.success(request, 'Username updated successfully.')
        return redirect('staff_profile')
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error updating username: {str(e)}')
        return redirect('staff_profile')


def staff_notifications(request):
    """
    Display all notifications for the current staff member.
    """
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
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
        paginator = Paginator(notifications, 15)
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
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error loading notifications: {str(e)}')
        return redirect('staff_dashboard')


@require_POST
def staff_mark_notification_read(request):
    """
    Mark a specific staff notification as read.
    """
    staff_id = request.session.get('admin_id')
    
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
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get content type for staff
        staff_content_type = ContentType.objects.get_for_model(Admin)
        
        # Mark all unread notifications for this staff member as read
        Notification.objects.filter(
            recipient_content_type=staff_content_type,
            recipient_object_id=current_staff.id,
            is_read=False
        ).update(is_read=True)
        
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
    staff_id = request.session.get('admin_id')
    
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
    staff_id = request.session.get('admin_id')
    
    if not staff_id:
        return redirect('admin_login')
    
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
        
        context = {
            'notification': notification,
            'current_staff': current_staff,
        }
        
        return render(request, 'notification_details.html', context)
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Notification.DoesNotExist:
        sweetify.error(request, 'Notification not found', timer=3000)
        return redirect('staff_notifications')
    except Exception as e:
        sweetify.error(request, f'Error loading notification: {str(e)}', timer=3000)
        return redirect('staff_notifications')