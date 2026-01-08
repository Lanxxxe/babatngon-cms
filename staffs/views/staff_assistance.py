from django.shortcuts import render, redirect
from admins.models import AssistanceRequest
from core.models import Admin
from admins.user_activity_utils import log_activity
from core.sms_util import send_sms, format_resolved_case


# Staff Assistance
def staff_assistance(request):
    """
    Display all assistance requests assigned to the current staff member.
    """
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
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
        
        # Log activity
        filter_info = []
        if status_filter:
            filter_info.append(f"status: {status_filter}")
        if type_filter:
            filter_info.append(f"type: {type_filter}")
        filter_desc = f" with filters ({', '.join(filter_info)})" if filter_info else ""
        
        log_activity(
            user=current_staff,
            activity_type='assistance_viewed',
            activity_category='case_management',
            description=f'{current_staff.get_full_name()} accessed assigned assistance requests{filter_desc}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'total_assistance': assistance_requests.count(), 'filters': {'status': status_filter, 'type': type_filter}}
        )
        
        context = {
            'assistance_requests': assistance_requests,
            'current_staff': current_staff,
            'status_filter': status_filter,
            'type_filter': type_filter,
        }
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    
    return render(request, 'staff_assistance.html', context)


















