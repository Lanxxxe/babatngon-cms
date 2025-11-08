from core.models import User
from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect
from admins.models import Complaint, AssistanceRequest
import sweetify


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
    logout(request)
    sweetify.toast(request, 'You have been logged out successfully.', timer=3000)
    return redirect('homepage')
