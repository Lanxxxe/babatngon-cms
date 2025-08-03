from django.shortcuts import render
from .models import Complaint
# Create your views here.
def admin_dashboard(request):

    # Get all complaints
    complaints = Complaint.objects.select_related('user').all().order_by('-created_at')

    # Metrics
    total_complaints = complaints.count()
    pending_complaints = complaints.filter(status='pending').count()
    in_progress_complaints = complaints.filter(status='in_progress').count()
    resolved_complaints = complaints.filter(status='resolved').count()

    # For recent complaints table (limit to 10 for dashboard)
    recent_complaints = complaints[:10]

    context = {
        'complaints': complaints,
        'recent_complaints': recent_complaints,
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
    }
    return render(request, 'admin_dashboard.html', context)

def admin_analytics(request):


    return render(request, 'admin_analytics.html')


def admin_complaints(request):

    complaints = Complaint.objects.all().order_by('-created_at')

    data = {
        'complaints': complaints
    }

    return render(request, 'admin_complaints.html', data)


def admin_resident(request):

    return render(request, 'admin_resident.html')

def admin_notification(request):


    return render(request, 'admin_notification.html')