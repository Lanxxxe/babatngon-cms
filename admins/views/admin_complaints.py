import sweetify
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from admins.models import Complaint
from core.models import Admin
from datetime import datetime
from admins.user_activity_utils import log_activity, log_case_activity


# Admin Complaint Management
def admin_complaints(request):
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    

    # Start with unassigned complaints by default
    complaints = Complaint.objects.select_related('user', 'assigned_to').filter(assigned_to__isnull=True)
    
    # Get filter parameters from request
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_filter = request.GET.get('category', '').strip()
    priority_filter = request.GET.get('priority', '').strip()
    designation_filter = request.GET.get('designation', '').strip()
    per_page = request.GET.get('per_page', '10')
    
    # If no designation filter is provided, default to unassigned
    if not designation_filter:
        designation_filter = 'unassigned'
    
    # If designation filter is explicitly set, override the default unassigned filter
    if designation_filter == 'assigned':
        complaints = Complaint.objects.select_related('user', 'assigned_to').filter(assigned_to__isnull=False)
    elif designation_filter == 'all':
        complaints = Complaint.objects.select_related('user', 'assigned_to').all()
    # If designation_filter is 'unassigned', keep the default unassigned filter
    
    # Validate per_page parameter
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10
    
    # Apply search filter
    if search_query:
        complaints = complaints.filter(
            Q(id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    
    # Apply category filter
    if category_filter:
        complaints = complaints.filter(category=category_filter)
    
    # Apply priority filter
    if priority_filter:
        complaints = complaints.filter(priority=priority_filter)
    
    # Apply designation filter (assigned/unassigned)
    # Note: Default filtering is already applied above, this section is now handled earlier
    
    # Order by creation date (newest first)
    complaints = complaints.order_by('-created_at')
    
    # Get total count before pagination
    total_complaints = complaints.count()
    
    # Pagination
    paginator = Paginator(complaints, per_page)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)
    
    # Get all staff members for assignment dropdown
    staff_members = Admin.objects.all().order_by('first_name', 'last_name').filter(role='staff')

    # Get unique categories and priorities for filter dropdowns
    categories = Complaint.objects.values_list('category', flat=True).distinct()
    priorities = Complaint.objects.values_list('priority', flat=True).distinct()

    # Log activity
    admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
    if admin_user:
        filter_info = []
        if search_query:
            filter_info.append(f"search: '{search_query}'")
        if status_filter:
            filter_info.append(f"status: {status_filter}")
        if category_filter:
            filter_info.append(f"category: {category_filter}")
        if priority_filter:
            filter_info.append(f"priority: {priority_filter}")
        if designation_filter:
            filter_info.append(f"designation: {designation_filter}")
        
        filter_desc = f" with filters ({', '.join(filter_info)})" if filter_info else ""
        
        log_activity(
            user=admin_user,
            activity_type='complaint_viewed',
            activity_category='case_management',
            description=f'{admin_user.get_full_name()} accessed complaint management page{filter_desc}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'total_results': total_complaints, 'filters': {'search': search_query, 'status': status_filter, 'category': category_filter, 'priority': priority_filter, 'designation': designation_filter}}
        )

    data = {
        'complaints': page_obj,  # This now contains the paginated results
        'page_obj': page_obj,
        'staff_members': staff_members,
        'categories': categories,
        'priorities': priorities,
        # Current filter values to maintain state
        'current_search': search_query,
        'current_status': status_filter,
        'current_category': category_filter,
        'current_priority': priority_filter,
        'current_designation': designation_filter,
        'current_per_page': per_page,
        # Counts for display
        'total_complaints': total_complaints,
        # Pagination info
        'start_index': page_obj.start_index() if page_obj else 0,
        'end_index': page_obj.end_index() if page_obj else 0,
    }

    return render(request, 'admin_complaints.html', data)

@require_POST
def assign_complaint(request):
    """
    Assign a complaint to a staff member.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    
    try:
        complaint_id = request.POST.get('complaint_id', '').strip()
        staff_id = request.POST.get('staff_id', '').strip()
        admin_remarks = request.POST.get('assignment_notes', '').strip()
        updated_priority = request.POST.get('priority', '').strip()
        
        complaint = Complaint.objects.get(id=complaint_id) 
        staff = Admin.objects.get(id=staff_id) if staff_id else None
        
        # Get current admin from session
        current_admin_id = request.session.get('admin_id')
        current_admin = Admin.objects.get(id=current_admin_id) if current_admin_id else None
        
        complaint.assigned_to = staff
        complaint.assigned_by = current_admin
        complaint.admin_remarks = admin_remarks
        complaint.updated_at = datetime.now()
        
        if updated_priority:
            complaint.priority = updated_priority

        complaint.status = 'assigned'

        complaint.save()
        
        # Log activity
        if current_admin:
            action = 'assigned' if staff else 'unassigned'
            staff_name = staff.get_full_name() if staff else 'No one'
            
            log_case_activity(
                user=current_admin,
                case=complaint,
                activity_type='complaint_assigned' if staff else 'complaint_updated',
                description=f'{current_admin.get_full_name()} {action} complaint #{complaint.id} - {complaint.title}' + (f' to {staff_name}' if staff else ''),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={
                    'assigned_to_id': staff.id if staff else None,
                    'assigned_to_name': staff_name,
                    'priority': complaint.priority,
                    'admin_remarks': admin_remarks
                }
            )
        
        if staff:
            sweetify.toast(request, f'Complaint #{complaint.id} assigned to {staff.full_name}', timer=2000)

        else:
            sweetify.toast(request, f'Complaint #{complaint.id} unassigned', timer=2000)

        return redirect('admin_complaints')
        
    except Exception as e:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='complaint_assigned',
                activity_category='case_management',
                description=f'{admin_user.get_full_name()} failed to assign complaint',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, f'Failed to assign complaint. Please try again. {e}', persistent=True, timer=3000)
        return redirect('complaint_details', complaint_id=complaint.id)

@require_POST 
def update_complaint_status(request):
    """
    Update complaint status.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        complaint_id = request.POST.get('complaint_id')
        new_status = request.POST.get('status')
        
        complaint = Complaint.objects.get(id=complaint_id)
        old_status = complaint.status
        complaint.status = new_status
        
        if new_status == 'resolved':
            from django.utils import timezone
            complaint.resolved_at = timezone.now()
            
        complaint.save()
        
        # Log activity
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            activity_type_map = {
                'resolved': 'complaint_resolved',
                'closed': 'complaint_closed',
                'in_progress': 'complaint_status_changed'
            }
            activity_type = activity_type_map.get(new_status, 'complaint_status_changed')
            
            log_case_activity(
                user=admin_user,
                case=complaint,
                activity_type=activity_type,
                description=f'{admin_user.get_full_name()} updated complaint #{complaint.id} - {complaint.title} status from {old_status} to {new_status}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'old_status': old_status, 'new_status': new_status}
            )
        
        sweetify.toast(request, f'Complaint #{complaint.id} status updated to {new_status.title()}', timer=2000)
        return JsonResponse({'success': True})
        
    except Exception as e:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='complaint_status_changed',
                activity_category='case_management',
                description=f'{admin_user.get_full_name()} failed to update complaint status',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'Failed to update status. Please try again.', timer=3000)
        return JsonResponse({'success': False, 'error': str(e)})


def complaint_details(request, complaint_id):
    """
    Get complaint details for modal display.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        staff = Admin.objects.all().order_by('first_name', 'last_name').filter(role='staff')
        complaint = Complaint.objects.select_related('user', 'assigned_to', 'assigned_by').get(id=complaint_id)
        
        # Format the complaint data
        complaint_data = {
            'id': complaint.id,
            'title': complaint.title,
            'category': complaint.category,
            'priority': complaint.priority,
            'status': complaint.status,
            'description': complaint.description,
            'created_at': complaint.created_at.strftime('%B %d, %Y at %I:%M %p') if complaint.created_at else None,
            
            # Resident information
            'resident_name': f"{complaint.user.first_name} {complaint.user.last_name}" if complaint.user else None,
            'resident_phone': getattr(complaint.user, 'phone', None),
            'resident_email': complaint.user.email if complaint.user else None,
            'resident_address': getattr(complaint.user, 'address', None),
            
            # Assignment information
            'assigned_to': complaint.assigned_to.get_full_name() if complaint.assigned_to else None,
            'assigned_by': complaint.assigned_by.get_full_name() if complaint.assigned_by else None,
            'assigned_date': None,  # This field doesn't exist in the model
            
            # Resolution information
            'resolved_by': None,  # This field doesn't exist in the model
            'resolved_date': complaint.resolved_at.strftime('%B %d, %Y at %I:%M %p') if complaint.resolved_at else None,
            'admin_remarks': complaint.admin_remarks or complaint.resolution_notes or None,
            
            # Location information
            'latitude': float(complaint.latitude) if complaint.latitude else None,
            'longitude': float(complaint.longitude) if complaint.longitude else None,
            'address': complaint.address or complaint.location or complaint.location_description or None,
            
            # Attachments
            'attachments': []
        }
        
        # Get attachments if they exist
        try:
            attachments = complaint.attachments.all()
            for attachment in attachments:
                complaint_data['attachments'].append({
                    'name': attachment.file.name.split('/')[-1] if attachment.file else 'Unknown',
                    'url': attachment.file.url if attachment.file else '#',
                    'size': f"{attachment.file.size // 1024} KB" if attachment.file and attachment.file.size else 'Unknown size'
                })
        except Exception:
            pass  # No attachments or error accessing them
        
        # Log activity
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_case_activity(
                user=admin_user,
                case=complaint,
                activity_type='complaint_viewed',
                description=f'{admin_user.get_full_name()} viewed complaint #{complaint.id} - {complaint.title}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'complaint_status': complaint.status, 'complaint_priority': complaint.priority, 'complaint_category': complaint.category}
            )
        
        context = {
            'complaint': complaint_data,
            'staffs' : staff
        }
        return render(request, 'admin_cases/complaint_details.html', context)
        
    except Complaint.DoesNotExist:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='complaint_viewed',
                activity_category='case_management',
                description=f'{admin_user.get_full_name()} attempted to view non-existent complaint #{complaint_id}',
                is_successful=False,
                error_message='Complaint not found',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'Complaint not found.', icon='error', timer=3000, persistent='Okay')
        return redirect('admin_complaints')
    
    except Exception as e:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='complaint_viewed',
                activity_category='case_management',
                description=f'{admin_user.get_full_name()} failed to view complaint #{complaint_id}',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'An error occurred.', icon='error', timer=3000, persistent='Okay')
        return redirect('admin_complaints')

