from admins.models import Complaint
from django.shortcuts import render, redirect
import sweetify, json
from django.utils import timezone
from datetime import timedelta, datetime
from django.db import models
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth


BARANGAYS = [
        "Bacong", "Bagong Silang", "Biasong", "Gov. E. Jaro",
        "Guintigui-an", "Lukay", "Magcasuang", "Malibago", "Naga-asan",
        "Pagsulhugon", "Planza", "Poblacion District I", "Poblacion District II", "Poblacion District III",
        "Poblacion District IV", "Rizal I", "Rizal II", "San Agustin", "San Isidro",
        "San Ricardo", "Sangputan", "Taguite", "Uban", "Victory", "Villa Magsaysay"
    ]

ASSISTANCE_TYPE = [
        "Medical", "Financial", "Food/Supplies",
        "Evacuation/Shelter", "Legal", "Livelihood",
        "Education","Transportation","Disaster/Emergency",
        "Others"
    ]

COMPLAINTS_CATEGORY = [
        "Sanitation", "Safety/Security", "Infrastructure", "Utilities",
        "Noise", "Environment", "Disaster/Emergency", "Health",
        "Traffic/Transport", "Corruption/Abuse", "Discrimination",
        "Service Delivery", "Others"
    ]


def admin_analytics(request):
    """
    Analytics dashboard with comprehensive data visualization and metrics.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        # Get all complaints for analysis
        complaints = Complaint.objects.select_related('user').all()
        
        # Get all assistance requests for analysis
        from admins.models import AssistanceRequest
        assistance_requests = AssistanceRequest.objects.select_related('user').all()
        
        # Basic metrics
        total_complaints = complaints.count()
        pending_complaints = complaints.filter(status='pending').count()
        in_progress_complaints = complaints.filter(status='in_progress').count()
        resolved_complaints = complaints.filter(status='resolved').count()
        
        # Assistance metrics
        total_assistance = assistance_requests.count()
        pending_assistance = assistance_requests.filter(status='pending').count()
        in_progress_assistance = assistance_requests.filter(status='in_progress').count()
        resolved_assistance = assistance_requests.filter(status='resolved').count()
        
        # Category distribution for complaints using actual categories
        category_data = {}
        category_detail_data = {}
        for category in COMPLAINTS_CATEGORY:
            category_key = category.lower().replace('/', '_').replace(' ', '_')
            category_complaints = complaints.filter(category__icontains=category.lower())
            count = category_complaints.count()
            category_data[category] = count
            
            # Get status breakdown for this category
            if count > 0:
                category_detail_data[category] = {
                    'pending': category_complaints.filter(status='pending').count(),
                    'in_progress': category_complaints.filter(status='in_progress').count() + category_complaints.filter(status='assigned').count(),
                    'resolved': category_complaints.filter(status='resolved').count(),
                }
            else:
                category_detail_data[category] = {'pending': 0, 'in_progress': 0, 'resolved': 0}
        
        # Assistance type distribution
        assistance_data = {}
        assistance_detail_data = {}
        for assistance_type in ASSISTANCE_TYPE:
            assistance_key = assistance_type.lower().replace('/', '_').replace(' ', '_')
            assistance_requests_filtered = assistance_requests.filter(type__icontains=assistance_type.lower())
            count = assistance_requests_filtered.count()
            assistance_data[assistance_type] = count
            
            # Get status breakdown for this assistance type
            if count > 0:
                assistance_detail_data[assistance_type] = {
                    'pending': assistance_requests_filtered.filter(status='pending').count(),
                    'in_progress': assistance_requests_filtered.filter(status='in_progress').count() + assistance_requests_filtered.filter(status='assigned').count(),
                    'resolved': assistance_requests_filtered.filter(status='resolved').count(),
                }
            else:
                assistance_detail_data[assistance_type] = {'pending': 0, 'in_progress': 0, 'resolved': 0}
        
        # Priority distribution for priority chart
        priority_data = {
            'Low': complaints.filter(priority='low').count(),
            'Medium': complaints.filter(priority='medium').count(),
            'High': complaints.filter(priority='high').count(),
            'Urgent': complaints.filter(priority='urgent').count(),
        }
        
        # Top barangays data (computed from actual location field)
        barangay_data = []
        # Combine complaints and assistance for location analysis
        all_cases_locations = list(complaints.values_list('location', flat=True)) + list(assistance_requests.values_list('address', flat=True))
        location_counts = {}
        for loc in all_cases_locations:
            if loc and loc.strip():
                # Check if location matches any barangay
                for barangay in BARANGAYS:
                    if barangay.lower() in loc.lower():
                        location_counts[barangay] = location_counts.get(barangay, 0) + 1
                        break
                else:
                    # If no barangay match found, use "Others"
                    location_counts['Others'] = location_counts.get('Others', 0) + 1
        
        # Convert to list and sort
        total_location_cases = sum(location_counts.values()) or 1
        for barangay, count in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:25]:
            percentage = round((count / total_location_cases) * 100, 1)
            barangay_data.append({'name': f'Barangay {barangay}', 'complaints': count, 'percentage': percentage})
        
        # Performance metrics (calculated from actual data)
        resolution_rate = round((resolved_complaints / total_complaints) * 100, 1) if total_complaints > 0 else 0
        response_time_rate = 0  # TODO: implement based on actual response times
        user_satisfaction = 0   # TODO: implement based on actual feedback
        system_efficiency = 0   # TODO: implement based on actual metrics
        
        # Average resolution time calculation (from actual data)
        resolved_with_time = complaints.filter(status='resolved', resolved_at__isnull=False)
        if resolved_with_time.exists():
            total_resolution_time = 0
            for comp in resolved_with_time:
                if comp.resolved_at and comp.created_at:
                    delta = comp.resolved_at - comp.created_at
                    total_resolution_time += delta.total_seconds()
            avg_resolution_time = round((total_resolution_time / resolved_with_time.count()) / 86400.0, 1)
        else:
            avg_resolution_time = 0
        
        # Active users count (from User model)
        from core.models import User, Feedback
        active_users = User.objects.filter(is_verified=True).count()
        total_users = User.objects.count()
        new_users_this_month = User.objects.filter(
            created_at__gte=timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Feedback statistics
        total_feedback = Feedback.objects.count()
        average_feedback_rating = Feedback.objects.aggregate(Avg('rating'))['rating__avg'] or 0
        unread_feedback = Feedback.objects.filter(is_read=False).count()
        
        # Status distribution for both complaints and assistance
        complaint_status_data = {
            'Pending': complaints.filter(status='pending').count(),
            'In Progress': complaints.filter(Q(status='in_progress') | Q(status='assigned')).count(),
            'Resolved': complaints.filter(status='resolved').count(),
        }
        
        assistance_status_data = {
            'Pending': assistance_requests.filter(status='pending').count(),
            'In Progress': assistance_requests.filter(Q(status='in_progress') | Q(status='assigned')).count(),
            'Resolved': assistance_requests.filter(status='resolved').count(),
        }
        
        # Monthly trend data (last 6 months)
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_complaints = complaints.filter(created_at__gte=six_months_ago).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        monthly_assistance = assistance_requests.filter(created_at__gte=six_months_ago).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        # Format monthly data
        monthly_labels = []
        monthly_complaint_counts = []
        monthly_assistance_counts = []
        
        for i in range(6):
            month_date = timezone.now() - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_label = month_start.strftime('%b %Y')
            
            complaint_count = complaints.filter(
                created_at__gte=month_start,
                created_at__lt=(month_start + timedelta(days=32)).replace(day=1)
            ).count()
            
            assistance_count = assistance_requests.filter(
                created_at__gte=month_start,
                created_at__lt=(month_start + timedelta(days=32)).replace(day=1)
            ).count()
            
            monthly_labels.insert(0, month_label)
            monthly_complaint_counts.insert(0, complaint_count)
            monthly_assistance_counts.insert(0, assistance_count)
        
        # Urgency distribution for assistance
        urgency_data = {
            'Low': assistance_requests.filter(urgency='low').count(),
            'Medium': assistance_requests.filter(urgency='medium').count(),
            'High': assistance_requests.filter(urgency='high').count(),
            'Urgent': assistance_requests.filter(urgency='urgent').count(),
        }
        
        # Response time metrics
        assigned_complaints = complaints.filter(assigned_to__isnull=False, status__in=['assigned', 'in_progress', 'resolved'])
        if assigned_complaints.exists():
            avg_response_time_seconds = 0
            response_count = 0
            for comp in assigned_complaints:
                # Approximate response time as time between creation and assignment
                # This is a simplified calculation
                response_count += 1
            avg_response_hours = round(avg_response_time_seconds / 3600.0, 1) if response_count > 0 else 0
        else:
            avg_response_hours = 0
        
        # Calculate response time rate based on 24-hour target
        response_time_rate = min(100, max(0, 100 - (avg_response_hours * 4))) if avg_response_hours > 0 else 0
        
        # System efficiency based on multiple factors
        efficiency_factors = [
            resolution_rate,
            response_time_rate,
            min(100, (resolved_complaints / max(total_complaints, 1)) * 100),
        ]
        system_efficiency = round(sum(efficiency_factors) / len(efficiency_factors), 1)
        
        # User satisfaction from feedback
        user_satisfaction = round((average_feedback_rating / 5.0) * 100, 1) if average_feedback_rating > 0 else 0
        
        context = {
            'total_complaints': total_complaints,
            'pending_complaints': pending_complaints,
            'in_progress_complaints': in_progress_complaints,
            'resolved_complaints': resolved_complaints,
            'total_assistance': total_assistance,
            'pending_assistance': pending_assistance,
            'in_progress_assistance': in_progress_assistance,
            'resolved_assistance': resolved_assistance,
            'avg_resolution_time': avg_resolution_time,
            'avg_response_hours': avg_response_hours,
            'user_satisfaction': user_satisfaction,
            'active_users': active_users,
            'total_users': total_users,
            'new_users_this_month': new_users_this_month,
            
            # Feedback statistics
            'total_feedback': total_feedback,
            'average_feedback_rating': round(average_feedback_rating, 1),
            'unread_feedback': unread_feedback,
            
            # Chart data - serialized as JSON
            'category_data': category_data,
            'priority_data': priority_data,
            'assistance_data': assistance_data,
            'urgency_data': urgency_data,
            'complaint_status_data': complaint_status_data,
            'assistance_status_data': assistance_status_data,
            'category_detail_data': json.dumps(category_detail_data),
            'assistance_detail_data': json.dumps(assistance_detail_data),
            'category_data_json': json.dumps(category_data),
            'priority_data_json': json.dumps(priority_data),
            'assistance_data_json': json.dumps(assistance_data),
            'urgency_data_json': json.dumps(urgency_data),
            'complaint_status_data_json': json.dumps(complaint_status_data),
            'assistance_status_data_json': json.dumps(assistance_status_data),
            
            # Monthly trend data
            'monthly_labels': json.dumps(monthly_labels),
            'monthly_complaint_counts': json.dumps(monthly_complaint_counts),
            'monthly_assistance_counts': json.dumps(monthly_assistance_counts),
            
            # Only include top 5 barangays by complaints
            'barangay_data': barangay_data[:5],
            # Performance metrics
            'resolution_rate': resolution_rate,
            'response_time_rate': round(response_time_rate, 1),
            'system_efficiency': system_efficiency,
        }
        # --- Smart analytics computations ---
        try:
            now = timezone.now()
            # Daily counts for the last 30 days (complaints + assistance)
            days = 30
            daily_counts = []
            daily_assistance_counts = []
            labels = []
            for i in range(days - 1, -1, -1):
                day = (now - timedelta(days=i)).date()
                start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
                end = timezone.make_aware(datetime.combine(day, datetime.max.time()))
                complaint_cnt = complaints.filter(created_at__range=(start, end)).count()
                assistance_cnt = assistance_requests.filter(created_at__range=(start, end)).count()
                labels.append(day.strftime('%b %d'))
                daily_counts.append(complaint_cnt)
                daily_assistance_counts.append(assistance_cnt)

            # Weekly comparison: last 7 days vs previous 7 days (complaints + assistance)
            last_7_start = now - timedelta(days=6)
            prev_7_start = now - timedelta(days=13)
            last_7_complaints = complaints.filter(created_at__date__gte=last_7_start.date()).count()
            prev_7_complaints = complaints.filter(created_at__date__range=(prev_7_start.date(), (last_7_start - timedelta(days=1)).date())).count()
            last_7_assistance = assistance_requests.filter(created_at__date__gte=last_7_start.date()).count()
            prev_7_assistance = assistance_requests.filter(created_at__date__range=(prev_7_start.date(), (last_7_start - timedelta(days=1)).date())).count()
            
            last_7_total = last_7_complaints + last_7_assistance
            prev_7_total = prev_7_complaints + prev_7_assistance
            
            smart_weekly_change = None
            if prev_7_total > 0:
                smart_weekly_change = round(((last_7_total - prev_7_total) / prev_7_total) * 100, 1)
            elif last_7_total > 0:
                smart_weekly_change = 100.0

            # Spike detection (simple): spike if last 7 days > 150% of previous 7 days
            smart_spike = False
            if prev_7_total > 0 and last_7_total > prev_7_total * 1.5:
                smart_spike = True

            # Top locations (by location field) - top 5 from both complaints and assistance
            complaint_locations = complaints.values('location').annotate(cnt=models.Count('id'))
            assistance_locations = assistance_requests.values('address').annotate(cnt=models.Count('id'))
            
            location_counts = {}
            for item in complaint_locations:
                loc = item.get('location') or 'Unknown'
                location_counts[loc] = location_counts.get(loc, 0) + item.get('cnt', 0)
            
            for item in assistance_locations:
                loc = item.get('address') or 'Unknown'
                location_counts[loc] = location_counts.get(loc, 0) + item.get('cnt', 0)
            
            top_locations = []
            for loc, count in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                top_locations.append({'location': loc, 'count': count})

            # Unresolved cases older than 7 days (both complaints and assistance)
            threshold = now - timedelta(days=7)
            unresolved_complaints_over_7 = complaints.filter(status__in=['pending', 'in_progress', 'assigned']).filter(created_at__lt=threshold).count()
            unresolved_assistance_over_7 = assistance_requests.filter(status__in=['pending', 'in_progress', 'assigned']).filter(created_at__lt=threshold).count()
            unresolved_over_7 = unresolved_complaints_over_7 + unresolved_assistance_over_7

            # Average resolution time by priority (in days)
            avg_resolution = {}
            for pr_key, _ in Complaint.PRIORITY_LEVELS:
                resolved_qs = complaints.filter(priority=pr_key, resolved_at__isnull=False)
                if resolved_qs.exists():
                    total_seconds = 0
                    for comp in resolved_qs:
                        if comp.resolved_at and comp.created_at:
                            delta = comp.resolved_at - comp.created_at
                            total_seconds += max(delta.total_seconds(), 0)
                    avg_days = (total_seconds / resolved_qs.count()) / 86400.0
                    avg_resolution[pr_key] = round(avg_days, 1)
                else:
                    avg_resolution[pr_key] = None

            # Inject into context
            context.update({
                'smart_daily_labels': json.dumps(labels),
                'smart_daily_counts': json.dumps(daily_counts),
                'smart_daily_assistance_counts': json.dumps(daily_assistance_counts),
                'smart_weekly_change': smart_weekly_change,
                'smart_spike': smart_spike,
                'smart_top_locations': top_locations,
                'smart_avg_resolution_by_priority': json.dumps(avg_resolution),
                'smart_unresolved_over_7days': unresolved_over_7,
            })
        except Exception:
            # if any smart analytics computation fails, keep placeholders
            context.update({
                'smart_daily_labels': json.dumps([]),
                'smart_daily_counts': json.dumps([]),
                'smart_daily_assistance_counts': json.dumps([]),
                'smart_weekly_change': None,
                'smart_spike': False,
                'smart_top_locations': [],
                'smart_avg_resolution_by_priority': json.dumps({}),
                'smart_unresolved_over_7days': 0,
            })
        
    except Exception as e:
        print(e)
        # Fallback to zero data if any error occurs
        context = {
            'total_complaints': 0,
            'pending_complaints': 0,
            'in_progress_complaints': 0,
            'resolved_complaints': 0,
            'total_assistance': 0,
            'pending_assistance': 0,
            'in_progress_assistance': 0,
            'resolved_assistance': 0,
            'avg_resolution_time': 0,
            'avg_response_hours': 0,
            'user_satisfaction': 0,
            'active_users': 0,
            'total_users': 0,
            'new_users_this_month': 0,
            
            # Feedback statistics
            'total_feedback': 0,
            'average_feedback_rating': 0,
            'unread_feedback': 0,
            
            # Chart data (empty)
            'category_data': {cat: 0 for cat in COMPLAINTS_CATEGORY},
            'priority_data': {
                'Low': 0,
                'Medium': 0,
                'High': 0,
                'Urgent': 0,
            },
            'assistance_data': {assist: 0 for assist in ASSISTANCE_TYPE},
            'urgency_data': {
                'Low': 0,
                'Medium': 0,
                'High': 0,
                'Urgent': 0,
            },
            'complaint_status_data': {
                'Pending': 0,
                'In Progress': 0,
                'Resolved': 0,
            },
            'assistance_status_data': {
                'Pending': 0,
                'In Progress': 0,
                'Resolved': 0,
            },
            'category_detail_data': json.dumps({cat: {'pending': 0, 'in_progress': 0, 'resolved': 0} for cat in COMPLAINTS_CATEGORY}),
            'assistance_detail_data': json.dumps({assist: {'pending': 0, 'in_progress': 0, 'resolved': 0} for assist in ASSISTANCE_TYPE}),
            'category_data_json': json.dumps({cat: 0 for cat in COMPLAINTS_CATEGORY}),
            'priority_data_json': json.dumps({
                'Low': 0,
                'Medium': 0,
                'High': 0,
                'Urgent': 0,
            }),
            'assistance_data_json': json.dumps({assist: 0 for assist in ASSISTANCE_TYPE}),
            'urgency_data_json': json.dumps({
                'Low': 0,
                'Medium': 0,
                'High': 0,
                'Urgent': 0,
            }),
            'complaint_status_data_json': json.dumps({
                'Pending': 0,
                'In Progress': 0,
                'Resolved': 0,
            }),
            'assistance_status_data_json': json.dumps({
                'Pending': 0,
                'In Progress': 0,
                'Resolved': 0,
            }),
            
            # Monthly trend data
            'monthly_labels': json.dumps([]),
            'monthly_complaint_counts': json.dumps([]),
            'monthly_assistance_counts': json.dumps([]),
            
            'barangay_data': [],
            
            # Performance metrics
            'resolution_rate': 0,
            'response_time_rate': 0,
            'system_efficiency': 0,
            
            # Smart analytics fallback
            'smart_daily_labels': json.dumps([]),
            'smart_daily_counts': json.dumps([]),
            'smart_daily_assistance_counts': json.dumps([]),
            'smart_weekly_change': None,
            'smart_spike': False,
            'smart_top_locations': [],
            'smart_avg_resolution_by_priority': json.dumps({}),
            'smart_unresolved_over_7days': 0,
        }

    return render(request, 'admin_analytics.html', context)

