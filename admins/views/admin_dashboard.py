from django.shortcuts import render, redirect
from admins.models import Complaint
from admins.models import AssistanceRequest
import sweetify

# Create your views here.
def admin_dashboard(request):

    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')

    # Get all complaints
    complaints = Complaint.objects.select_related('user').all().order_by('-created_at')
    assistance = AssistanceRequest.objects.select_related('user').all().order_by('-created_at')

    # Metrics
    total_complaints = complaints.count()
    pending_complaints = complaints.filter(status='pending').count()
    in_progress_complaints = complaints.filter(status='in_progress').count()
    resolved_complaints = complaints.filter(status='resolved').count()

    # For recent complaints table (limit to 10 for dashboard)
    recent_complaints = complaints[:5]
    recent_assistance = assistance[:5]

    context = {
        'complaints': complaints,
        'recent_complaints': recent_complaints,
        'recent_assistance': recent_assistance,
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
    }
    return render(request, 'admin_dashboard.html', context)

