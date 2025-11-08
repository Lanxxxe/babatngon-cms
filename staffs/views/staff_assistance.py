from django.shortcuts import render, redirect
from admins.models import AssistanceRequest
from core.models import Admin


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
        
        context = {
            'assistance_requests': assistance_requests,
            'current_staff': current_staff,
            'status_filter': status_filter,
            'type_filter': type_filter,
        }
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    
    return render(request, 'staff_assistance.html', context)


















