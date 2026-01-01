from django.shortcuts import render, redirect
from admins.models import Complaint, AssistanceRequest
from core.models import User, Feedback
import sweetify
import json
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q

# Create your views here.
def admin_dashboard(request):
 
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')

    # Get all complaints and assistance
    complaints = Complaint.objects.select_related('user').all().order_by('-created_at')
    assistance = AssistanceRequest.objects.select_related('user').all().order_by('-created_at')

    # Basic Metrics
    total_complaints = complaints.count()
    pending_complaints = complaints.filter(status='pending').count()
    in_progress_complaints = complaints.filter(Q(status='in_progress') | Q(status='assigned')).count()
    resolved_complaints = complaints.filter(status='resolved').count()
    
    total_assistance = assistance.count()
    pending_assistance = assistance.filter(status='pending').count()
    in_progress_assistance = assistance.filter(Q(status='in_progress') | Q(status='assigned')).count()
    resolved_assistance = assistance.filter(status='resolved').count()

    # Calculate Resolution Rates
    resolution_rate = round((resolved_complaints / total_complaints) * 100, 1) if total_complaints > 0 else 0
    assistance_resolution_rate = round((resolved_assistance / total_assistance) * 100, 1) if total_assistance > 0 else 0
    
    # Average Resolution Time (in days)
    resolved_with_time = complaints.filter(status='resolved', resolved_at__isnull=False)
    if resolved_with_time.exists():
        total_time = sum([(c.resolved_at - c.created_at).total_seconds() for c in resolved_with_time if c.resolved_at and c.created_at])
        avg_resolution_days = round(total_time / (resolved_with_time.count() * 86400), 1)
    else:
        avg_resolution_days = 0

    # Get category distribution for complaints (top 5)
    category_counts = complaints.values('category').annotate(count=Count('id')).order_by('-count')[:5]
    category_labels = [item['category'] for item in category_counts]
    category_data = [item['count'] for item in category_counts]
    
    # Get monthly trend data (last 6 months)
    monthly_labels = []
    monthly_complaint_counts = []
    monthly_assistance_counts = []
    
    for i in range(5, -1, -1):
        month_date = timezone.now() - timedelta(days=30*i)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        
        complaint_count = complaints.filter(created_at__gte=month_start, created_at__lte=month_end).count()
        assistance_count = assistance.filter(created_at__gte=month_start, created_at__lte=month_end).count()
        
        monthly_labels.append(month_start.strftime('%b'))
        monthly_complaint_counts.append(complaint_count)
        monthly_assistance_counts.append(assistance_count)
    
    # Recent items for tables
    recent_complaints = complaints[:5]
    recent_assistance = assistance[:5]

    # Urgent Cases
    urgent_complaints = complaints.filter(priority='urgent')[:3]
    urgent_assistance = assistance.filter(urgency='urgent')[:3]
    
    # Additional user metrics
    total_users = User.objects.filter(is_verified=True).count()
    new_users_this_month = User.objects.filter(
        created_at__gte=timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ).count()
    
    # This month vs last month comparison
    this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    
    complaints_this_month = complaints.filter(created_at__gte=this_month_start).count()
    complaints_last_month = complaints.filter(
        created_at__gte=last_month_start, 
        created_at__lt=this_month_start
    ).count()
    
    if complaints_last_month > 0:
        complaint_change_pct = round(((complaints_this_month - complaints_last_month) / complaints_last_month) * 100, 1)
    else:
        complaint_change_pct = 0
    
    # Assistance comparison
    assistance_this_month = assistance.filter(created_at__gte=this_month_start).count()
    assistance_last_month = assistance.filter(
        created_at__gte=last_month_start, 
        created_at__lt=this_month_start
    ).count()
    
    if assistance_last_month > 0:
        assistance_change_pct = round(((assistance_this_month - assistance_last_month) / assistance_last_month) * 100, 1)
    else:
        assistance_change_pct = 0

    context = {
        # Complaint metrics
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
        'resolution_rate': resolution_rate,
        'avg_resolution_days': avg_resolution_days,
        'complaints_this_month': complaints_this_month,
        'complaint_change_pct': complaint_change_pct,
        
        # Assistance metrics
        'total_assistance': total_assistance,
        'pending_assistance': pending_assistance,
        'in_progress_assistance': in_progress_assistance,
        'resolved_assistance': resolved_assistance,
        'assistance_resolution_rate': assistance_resolution_rate,
        'assistance_this_month': assistance_this_month,
        'assistance_change_pct': assistance_change_pct,
        
        # User metrics
        'total_users': total_users,
        'new_users_this_month': new_users_this_month,
        
        # Chart data
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_complaint_counts': json.dumps(monthly_complaint_counts),
        'monthly_assistance_counts': json.dumps(monthly_assistance_counts),
        
        # Table data
        'recent_complaints': recent_complaints,
        'recent_assistance': recent_assistance,
        'urgent_complaints': urgent_complaints,
        'urgent_assistance': urgent_assistance,
    }
    return render(request, 'admin_dashboard.html', context)

