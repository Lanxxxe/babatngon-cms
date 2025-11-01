from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from admins.models import AssistanceRequest
from core.models import Admin
from datetime import datetime
import sweetify

# Admin Assistance Management
def admin_assistance(request):
    """
    Display all assistance requests for admin management.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    # Start with unassigned assistance requests by default
    assistance_requests = AssistanceRequest.objects.select_related('user', 'assigned_to').filter(assigned_to__isnull=True)
    
    # Get filter parameters from request
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    type_filter = request.GET.get('type', '').strip()
    urgency_filter = request.GET.get('urgency', '').strip()
    designation_filter = request.GET.get('designation', '').strip()
    per_page = request.GET.get('per_page', '10')
    
    # If no designation filter is provided, default to unassigned
    if not designation_filter:
        designation_filter = 'unassigned'
    
    # If designation filter is explicitly set, override the default unassigned filter
    if designation_filter == 'assigned':
        assistance_requests = AssistanceRequest.objects.select_related('user', 'assigned_to').filter(assigned_to__isnull=False)
    elif designation_filter == 'all':
        assistance_requests = AssistanceRequest.objects.select_related('user', 'assigned_to').all()
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
        assistance_requests = assistance_requests.filter(
            Q(id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter:
        assistance_requests = assistance_requests.filter(status=status_filter)
    
    # Apply type filter
    if type_filter:
        assistance_requests = assistance_requests.filter(type=type_filter)
    
    # Apply urgency filter
    if urgency_filter:
        assistance_requests = assistance_requests.filter(urgency=urgency_filter)
    
    # Order by creation date (newest first)
    assistance_requests = assistance_requests.order_by('-created_at')
    
    # Get total count before pagination
    total_assistance_requests = assistance_requests.count()
    
    # Pagination
    paginator = Paginator(assistance_requests, per_page)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)
    
    # Get all staff members for assignment dropdown
    staff_members = Admin.objects.all().order_by('first_name', 'last_name').filter(role='staff')

    # Get unique types and urgencies for filter dropdowns
    types = AssistanceRequest.objects.values_list('type', flat=True).distinct()
    urgencies = AssistanceRequest.objects.values_list('urgency', flat=True).distinct()

    data = {
        'assistance_requests': page_obj,  # This now contains the paginated results
        'page_obj': page_obj,
        'staff_members': staff_members,
        'types': types,
        'urgencies': urgencies,
        # Current filter values to maintain state
        'current_search': search_query,
        'current_status': status_filter,
        'current_type': type_filter,
        'current_urgency': urgency_filter,
        'current_designation': designation_filter,
        'current_per_page': per_page,
        # Counts for display
        'total_assistance_requests': total_assistance_requests,
        # Pagination info
        'start_index': page_obj.start_index() if page_obj else 0,
        'end_index': page_obj.end_index() if page_obj else 0,
    }

    return render(request, 'admin_assistance.html', data)


def assistance_details(request, assistance_id):
    """
    Get assistance request details for modal display.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        staff = Admin.objects.all().order_by('first_name', 'last_name').filter(role='staff')
        assistance = AssistanceRequest.objects.select_related('user', 'assigned_to').get(id=assistance_id)
        
        # Format the assistance data
        assistance_data = {
            'id': assistance.id,
            'title': assistance.title,
            'type': assistance.type,
            'description': assistance.description,
            'requested_date': assistance.created_at.strftime('%B %d, %Y at %I:%M %p') if assistance.created_at else None,
            'urgency_level': assistance.urgency.title() if assistance.urgency else None,
            'status': assistance.status.title() if assistance.status else None,
            
            # Resident information
            'resident_name': f"{assistance.user.first_name} {assistance.user.last_name}" if assistance.user else None,
            'resident_phone': getattr(assistance.user, 'phone', None),
            'resident_email': assistance.user.email if assistance.user else None,
            'resident_address': getattr(assistance.user, 'address', None),
            
            # Assignment information
            'assigned_to': assistance.assigned_to.get_full_name() if assistance.assigned_to else None,
            'assigned_by': assistance.assigned_by.get_full_name() if assistance.assigned_by else None,
            'assigned_date': assistance.assigned_date.strftime('%B %d, %Y at %I:%M %p') if assistance.assigned_date else None,
            
            # Completion information
            'completed_by': assistance.completed_by.get_full_name() if assistance.completed_by else None,
            'completed_date': assistance.completed_at.strftime('%B %d, %Y at %I:%M %p') if assistance.completed_at else None,
            'admin_notes': assistance.admin_remarks if assistance.admin_remarks else assistance.completion_notes if assistance.completion_notes else None,
            
            # Location information
            'latitude': float(assistance.latitude) if assistance.latitude else None,
            'longitude': float(assistance.longitude) if assistance.longitude else None,
            
            # Attachments
            'attachments': []
        }
        
        # Get attachments if they exist
        if hasattr(assistance, 'attachments'):
            attachments = assistance.attachments.all()
            for attachment in attachments:
                assistance_data['attachments'].append({
                    'name': attachment.file.name.split('/')[-1] if attachment.file else 'Unknown',
                    'url': attachment.file.url if attachment.file else '',
                    'size': f"{attachment.file.size // 1024} KB" if attachment.file and attachment.file.size else 'Unknown size'
                })
        
        context = {
            'assistance': assistance_data,
            'staffs': staff,
        }
        return render(request, 'admin_cases/assistance_details.html', context)

    except AssistanceRequest.DoesNotExist:
        sweetify.error(request, 'Assistance request not found.', icon='error', timer=3000, persistent='Okay')
        return redirect('admin_assistance')

    except Exception as e:
        print(e)
        sweetify.error(request, 'Failed to load assistance details. Please try again.', icon='error', timer=3000, persistent='Okay')
        return redirect('admin_assistance')


@require_POST
def assign_assistance(request):
    """
    Assign an assistance request to a staff member.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        assistance_id = request.POST.get('assistance_id')
        staff_id = request.POST.get('staff_id')
        admin_remarks = request.POST.get('assignment_notes', '').strip()
        updated_urgency = request.POST.get('urgency', '').strip()

        assistance = AssistanceRequest.objects.get(id=assistance_id)
        staff = Admin.objects.get(id=staff_id) if staff_id else None
        
        # Get current admin from session
        current_admin_id = request.session.get('admin_id')

        current_admin = Admin.objects.get(id=current_admin_id) if current_admin_id else None
        
        assistance.assigned_to = staff
        assistance.assigned_by = current_admin
        assistance.admin_remarks = admin_remarks
        assistance.assigned_date = datetime.now()

        assistance.status = 'assigned'
        assistance.urgency = updated_urgency if updated_urgency else assistance.urgency

        if staff:
            sweetify.toast(request, f'Assistance request #{assistance.id} assigned to {staff.full_name}', timer=2000)
        else:
             sweetify.toast(request, f'Assistance request #{assistance.id} unassigned', timer=2000)

        assistance.save()

        return redirect('assistance_details', assistance_id=assistance.id)

    except Exception as e:
        sweetify.error(request, f'Failed to assign assistance request. Please try again. {e}', persistent=True, timer=3000)
        return redirect('assistance_details', assistance_id=assistance_id)


@require_POST 
def update_assistance_status(request):
    """
    Update assistance request status.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:
        assistance_id = request.POST.get('assistance_id')
        new_status = request.POST.get('status')
        
        assistance = AssistanceRequest.objects.get(id=assistance_id)
        assistance.status = new_status
        
        if new_status == 'completed':
            from django.utils import timezone
            assistance.completed_at = timezone.now()
            
        assistance.save()
        
        sweetify.toast(request, f'Assistance request #{assistance.id} status updated to {new_status.title()}', timer=2000)
        return JsonResponse({'success': True})
        
    except Exception as e:
        sweetify.error(request, 'Failed to update status. Please try again.', timer=3000)
        return JsonResponse({'success': False, 'error': str(e)})

