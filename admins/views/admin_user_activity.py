from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from admins.models import UserActivity
from core.models import Admin
from admins.user_activity_utils import log_activity, ACTIVITY_TYPES, ACTIVITY_CATEGORIES
import sweetify


def admin_user_activity(request):
    """
    Display all user activities with filtering and search capabilities.
    """
    admin_id = request.session.get('admin_id')
    
    if not admin_id:
        return redirect('admin_login')
    
    try:
        current_admin = Admin.objects.get(id=admin_id)
        
        # Base query
        activities = UserActivity.objects.all().select_related(
            'user_content_type',
            'related_complaint',
            'related_assistance'
        ).order_by('-created_at')
        
        # Get filter parameters
        user_type_filter = request.GET.get('user_type', '')
        activity_type_filter = request.GET.get('activity_type', '')
        category_filter = request.GET.get('category', '')
        status_filter = request.GET.get('status', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        search_query = request.GET.get('search', '').strip()
        
        # Apply filters
        if user_type_filter:
            activities = activities.filter(user_type=user_type_filter)
        
        if activity_type_filter:
            activities = activities.filter(activity_type=activity_type_filter)
        
        if category_filter:
            activities = activities.filter(activity_category=category_filter)
        
        if status_filter:
            if status_filter == 'successful':
                activities = activities.filter(is_successful=True)
            elif status_filter == 'failed':
                activities = activities.filter(is_successful=False)
        
        # Date range filters
        if date_from:
            try:
                date_from_obj = timezone.datetime.strptime(date_from, '%Y-%m-%d')
                activities = activities.filter(created_at__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = timezone.datetime.strptime(date_to, '%Y-%m-%d')
                # Add 1 day to include the entire end date
                date_to_obj = date_to_obj + timedelta(days=1)
                activities = activities.filter(created_at__lt=date_to_obj)
            except ValueError:
                pass
        
        # Search functionality
        if search_query:
            activities = activities.filter(
                Q(user_name__icontains=search_query) |
                Q(user_email__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(ip_address__icontains=search_query)
            )
        
        # Calculate statistics
        total_activities = activities.count()
        successful_activities = activities.filter(is_successful=True).count()
        failed_activities = activities.filter(is_successful=False).count()
        
        # Get activity counts by category
        category_stats = activities.values('activity_category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get activity counts by user type
        user_type_stats = activities.values('user_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get recent activities (last 24 hours)
        last_24h = timezone.now() - timedelta(hours=24)
        recent_activities_count = activities.filter(created_at__gte=last_24h).count()
        
        # Pagination
        paginator = Paginator(activities, 15)  # Show 15 activities per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get unique values for filters (distinct user types only)
        user_types = UserActivity.objects.values_list('user_type', flat=True).distinct().order_by('user_type')
        
        # Log activity
        filter_info = []
        if user_type_filter:
            filter_info.append(f"user_type: {user_type_filter}")
        if activity_type_filter:
            filter_info.append(f"activity_type: {activity_type_filter}")
        if category_filter:
            filter_info.append(f"category: {category_filter}")
        if status_filter:
            filter_info.append(f"status: {status_filter}")
        if search_query:
            filter_info.append(f"search: {search_query}")
        filter_desc = f" with filters ({', '.join(filter_info)})" if filter_info else ""
        
        log_activity(
            user=current_admin,
            activity_type='report_generated',
            activity_category='reporting',
            description=f'{current_admin.get_full_name()} viewed user activity logs{filter_desc}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={
                'total_activities': total_activities,
                'filters_applied': len(filter_info),
                'search_query': search_query
            }
        )
        
        context = {
            'current_admin': current_admin,
            'activities': page_obj,
            'page_obj': page_obj,
            
            # Statistics
            'total_activities': total_activities,
            'successful_activities': successful_activities,
            'failed_activities': failed_activities,
            'recent_activities_count': recent_activities_count,
            'category_stats': category_stats,
            'user_type_stats': user_type_stats,
            
            # Filter options
            'user_types': user_types,
            'activity_types': ACTIVITY_TYPES,
            'activity_categories': ACTIVITY_CATEGORIES,
            
            # Current filter values
            'user_type_filter': user_type_filter,
            'activity_type_filter': activity_type_filter,
            'category_filter': category_filter,
            'status_filter': status_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search_query': search_query,
        }
        
        return render(request, 'admin_user_activity.html', context)
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error loading user activities: {str(e)}')
        return redirect('admin_dashboard')


def export_user_activity(request):
    """
    Export user activity logs to CSV.
    """
    admin_id = request.session.get('admin_id')
    
    if not admin_id:
        return redirect('admin_login')
    
    try:
        import csv
        from django.http import HttpResponse
        
        current_admin = Admin.objects.get(id=admin_id)
        
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="user_activity_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Timestamp',
            'User Name',
            'User Type',
            'User Email',
            'Activity Type',
            'Category',
            'Description',
            'Status',
            'IP Address',
            'Error Message'
        ])
        
        # Apply same filters as the main view
        activities = UserActivity.objects.all().order_by('-created_at')
        
        user_type_filter = request.GET.get('user_type', '')
        activity_type_filter = request.GET.get('activity_type', '')
        category_filter = request.GET.get('category', '')
        status_filter = request.GET.get('status', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        search_query = request.GET.get('search', '').strip()
        
        if user_type_filter:
            activities = activities.filter(user_type=user_type_filter)
        if activity_type_filter:
            activities = activities.filter(activity_type=activity_type_filter)
        if category_filter:
            activities = activities.filter(activity_category=category_filter)
        if status_filter:
            if status_filter == 'successful':
                activities = activities.filter(is_successful=True)
            elif status_filter == 'failed':
                activities = activities.filter(is_successful=False)
        if date_from:
            try:
                date_from_obj = timezone.datetime.strptime(date_from, '%Y-%m-%d')
                activities = activities.filter(created_at__gte=date_from_obj)
            except ValueError:
                pass
        if date_to:
            try:
                date_to_obj = timezone.datetime.strptime(date_to, '%Y-%m-%d')
                date_to_obj = date_to_obj + timedelta(days=1)
                activities = activities.filter(created_at__lt=date_to_obj)
            except ValueError:
                pass
        if search_query:
            activities = activities.filter(
                Q(user_name__icontains=search_query) |
                Q(user_email__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Write data rows
        for activity in activities:
            writer.writerow([
                activity.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                activity.user_name,
                activity.user_type,
                activity.user_email or '',
                activity.get_activity_type_display(),
                activity.get_activity_category_display(),
                activity.description,
                'Success' if activity.is_successful else 'Failed',
                activity.ip_address or '',
                activity.error_message or ''
            ])
        
        # Log export activity
        log_activity(
            user=current_admin,
            activity_type='export_data',
            activity_category='reporting',
            description=f'{current_admin.get_full_name()} exported user activity logs',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'total_records': activities.count()}
        )
        
        return response
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error exporting activities: {str(e)}')
        return redirect('admin_user_activity')
