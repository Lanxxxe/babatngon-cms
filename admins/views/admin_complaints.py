import sweetify
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from admins.models import Complaint
from core.models import Admin


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
        complaint_id = request.POST.get('complaint_id')
        staff_id = request.POST.get('staff_id')
        
        complaint = Complaint.objects.get(id=complaint_id) 
        staff = Admin.objects.get(id=staff_id) if staff_id else None
        
        # Get current admin from session
        current_admin_id = request.session.get('admin_id')
        current_admin = Admin.objects.get(id=current_admin_id) if current_admin_id else None
        
        complaint.assigned_to = staff
        complaint.assigned_by = current_admin
        
        complaint.status = 'pending'
 
        if staff:
            sweetify.toast(request, f'Complaint #{complaint.id} assigned to {staff.full_name}', timer=2000)
 
        else:
            sweetify.toast(request, f'Complaint #{complaint.id} unassigned', timer=2000)

        complaint.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        sweetify.error(request, f'Failed to assign complaint. Please try again. {e}', persistent=True, timer=3000)
        return JsonResponse({'success': False, 'error': str(e)})

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
        complaint.status = new_status
        
        if new_status == 'resolved':
            from django.utils import timezone
            complaint.resolved_at = timezone.now()
            
        complaint.save()
        
        sweetify.toast(request, f'Complaint #{complaint.id} status updated to {new_status.title()}', timer=2000)
        return JsonResponse({'success': True})
        
    except Exception as e:
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
        
        return JsonResponse({
            'success': True,
            'complaint': complaint_data
        })
        
    except Complaint.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Complaint not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

