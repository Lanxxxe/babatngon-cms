from core.models import User
from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect
from admins.models import Complaint, AssistanceRequest
import sweetify
from admins.user_activity_utils import log_activity, log_logout


def resident_dashboard(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to access the dashboard.', timer=3000)
        return redirect('homepage')
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    # Complaints stats
    total_complaints = Complaint.objects.filter(user=user).count()
    pending_complaints = Complaint.objects.filter(user=user, status='pending').count()
    in_progress_complaints = Complaint.objects.filter(user=user, status='in_progress').count()
    resolved_complaints = Complaint.objects.filter(user=user, status='resolved').count()
    recent_complaints = Complaint.objects.filter(user=user).order_by('-created_at')[:5]

    # Assistance stats
    total_assistance = AssistanceRequest.objects.filter(user=user).count()
    pending_assistance = AssistanceRequest.objects.filter(user=user, status='pending').count()
    in_progress_assistance = AssistanceRequest.objects.filter(user=user, status='in_progress').count()
    completed_assistance = AssistanceRequest.objects.filter(user=user, status='completed').count()
    recent_assistance = AssistanceRequest.objects.filter(user=user).order_by('-created_at')[:5]

    # Log activity
    log_activity(
        user=user,
        activity_type='other',
        activity_category='system',
        description=f'{user.get_full_name()} accessed resident dashboard',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        metadata={
            'total_complaints': total_complaints,
            'pending_complaints': pending_complaints,
            'total_assistance': total_assistance,
            'pending_assistance': pending_assistance
        }
    )

    context = {
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
        'recent_complaints': recent_complaints,
        'total_assistance': total_assistance,
        'pending_assistance': pending_assistance,
        'in_progress_assistance': in_progress_assistance,
        'completed_assistance': completed_assistance,
        'recent_assistance': recent_assistance,
    }
    return render(request, 'resident_dashboard.html', context)


# Logout View
def resident_logout(request):
    # Get user info before clearing session
    user_id = request.session.get('resident_id')
    
    # Log logout
    if user_id:
        try:
            user = User.objects.filter(id=user_id).first()
            if user:
                log_logout(
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
        except Exception:
            pass  # If logging fails, continue with logout
    
    logout(request)
    sweetify.toast(request, 'You have been logged out successfully.', timer=3000)
    return redirect('homepage')
