from django.shortcuts import render, redirect
from admins.models import Complaint, AssistanceRequest
from core.models import Admin
from admins.user_activity_utils import log_activity
import json
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q


# Staff Dashboard
def staff_dashboard(request):
    """
    Staff dashboard showing assigned complaints and assistance requests.
    """
    # Get current staff member from session
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        # Redirect to login if no staff session
        return redirect('staff_login')
    
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
        in_progress_complaints = assigned_complaints.filter(Q(status='in_progress') | Q(status='assigned')).count()
        resolved_complaints = assigned_complaints.filter(status='resolved').count()
        
        # Calculate metrics for assigned assistance requests
        total_assistance = assigned_assistance.count()
        pending_assistance = assigned_assistance.filter(status='pending').count()
        in_progress_assistance = assigned_assistance.filter(Q(status='in_progress') | Q(status='assigned')).count()
        resolved_assistance = assigned_assistance.filter(status='resolved').count()
        
        # Calculate Resolution Rates
        resolution_rate = round((resolved_complaints / total_complaints) * 100, 1) if total_complaints > 0 else 0
        assistance_completion_rate = round((resolved_assistance / total_assistance) * 100, 1) if total_assistance > 0 else 0
        
        # Average Resolution Time (in days) for assigned complaints
        resolved_with_time = assigned_complaints.filter(status='resolved', resolved_at__isnull=False)
        if resolved_with_time.exists():
            total_time = sum([(c.resolved_at - c.created_at).total_seconds() for c in resolved_with_time if c.resolved_at and c.created_at])
            avg_resolution_days = round(total_time / (resolved_with_time.count() * 86400), 1)
        else:
            avg_resolution_days = 0
        
        # Get category distribution for assigned complaints (top 5)
        category_counts = assigned_complaints.values('category').annotate(count=Count('id')).order_by('-count')[:5]
        category_labels = [item['category'] for item in category_counts]
        category_data = [item['count'] for item in category_counts]
        
        # Get monthly trend data for assigned cases (last 6 months)
        monthly_labels = []
        monthly_complaint_counts = []
        monthly_assistance_counts = []
        monthly_resolved_counts = []
        
        for i in range(5, -1, -1):
            month_date = timezone.now() - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            # Assigned complaints in this month
            month_complaints = assigned_complaints.filter(created_at__gte=month_start, created_at__lte=month_end).count()
            month_assistance = assigned_assistance.filter(created_at__gte=month_start, created_at__lte=month_end).count()
            month_resolved = assigned_complaints.filter(resolved_at__gte=month_start, resolved_at__lte=month_end).count()
            
            monthly_labels.append(month_start.strftime('%b'))
            monthly_complaint_counts.append(month_complaints)
            monthly_assistance_counts.append(month_assistance)
            monthly_resolved_counts.append(month_resolved)
        
        # This month vs last month comparison
        this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        complaints_this_month = assigned_complaints.filter(created_at__gte=this_month_start).count()
        complaints_last_month = assigned_complaints.filter(
            created_at__gte=last_month_start,
            created_at__lt=this_month_start
        ).count()
        
        if complaints_last_month > 0:
            complaint_change_pct = round(((complaints_this_month - complaints_last_month) / complaints_last_month) * 100, 1)
        else:
            complaint_change_pct = 0 if complaints_this_month == 0 else 100.0
        
        # Assistance comparison
        assistance_this_month = assigned_assistance.filter(created_at__gte=this_month_start).count()
        assistance_last_month = assigned_assistance.filter(
            created_at__gte=last_month_start,
            created_at__lt=this_month_start
        ).count()
        
        if assistance_last_month > 0:
            assistance_change_pct = round(((assistance_this_month - assistance_last_month) / assistance_last_month) * 100, 1)
        else:
            assistance_change_pct = 0 if assistance_this_month == 0 else 100.0
        
        # Resolved this month
        resolved_this_month = assigned_complaints.filter(
            resolved_at__gte=this_month_start,
            status='resolved'
        ).count()
        
        # Get recent assigned complaints (limit to 10 for dashboard display)
        recent_complaints = assigned_complaints[:10]
        
        # Get recent assigned assistance requests (limit to 5)
        recent_assistance = assigned_assistance[:5]
        
        # Get high priority complaints assigned to this staff
        high_priority_complaints = assigned_complaints.filter(
            priority__in=['high', 'urgent']
        ).exclude(status='resolved')[:5]
        
        # Log activity
        log_activity(
            user=current_staff,
            activity_type='dashboard_accessed',
            activity_category='system',
            description=f'{current_staff.get_full_name()} accessed staff dashboard',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={
                'total_assigned_complaints': total_complaints,
                'total_assigned_assistance': total_assistance,
                'pending_complaints': pending_complaints,
                'pending_assistance': pending_assistance
            }
        )
        
        context = {
            'current_staff': current_staff,
            
            # Complaint metrics
            'total_complaints': total_complaints,
            'pending_complaints': pending_complaints,
            'in_progress_complaints': in_progress_complaints,
            'resolved_complaints': resolved_complaints,
            'resolution_rate': resolution_rate,
            'avg_resolution_days': avg_resolution_days,
            'complaints_this_month': complaints_this_month,
            'complaint_change_pct': complaint_change_pct,
            'resolved_this_month': resolved_this_month,
            
            # Assistance metrics
            'assistance_requests': total_assistance,
            'total_assistance': total_assistance,
            'pending_assistance': pending_assistance,
            'in_progress_assistance': in_progress_assistance,
            'resolved_assistance': resolved_assistance,
            'assistance_completion_rate': assistance_completion_rate,
            'assistance_this_month': assistance_this_month,
            'assistance_change_pct': assistance_change_pct,
            
            # Chart data
            'category_labels': json.dumps(category_labels),
            'category_data': json.dumps(category_data),
            'monthly_labels': json.dumps(monthly_labels),
            'monthly_complaint_counts': json.dumps(monthly_complaint_counts),
            'monthly_assistance_counts': json.dumps(monthly_assistance_counts),
            'monthly_resolved_counts': json.dumps(monthly_resolved_counts),
            
            # Data for tables/lists
            'recent_complaints': recent_complaints,
            'recent_assistance': recent_assistance,
            'high_priority_complaints': high_priority_complaints,
            
            # For charts - complaint categories
            'assigned_complaints': assigned_complaints,
        }
        
    except Admin.DoesNotExist:
        # If staff not found, redirect to login
        return redirect('staff_login')
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






