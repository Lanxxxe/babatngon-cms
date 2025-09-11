from django.shortcuts import render, redirect
from admins.models import Complaint, AssistanceRequest
from core.models import Admin
from django.db.models import Count

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