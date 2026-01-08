from django.shortcuts import render, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from core.models import SMSLogs
import sweetify


def admin_sms_logs(request):
    """View to display SMS logs to admin users"""
    # Check if admin is logged in
    if not request.session.get('admin_id'):
        sweetify.error(request, 'Please login to access this page.', timer=3000)
        return redirect('admin_login')
    
    # Get all SMS logs ordered by most recent first
    sms_logs_list = SMSLogs.objects.all().order_by('-created_at')
    
    # Calculate statistics (before pagination)
    total_sms = sms_logs_list.count()
    successful_sms = sms_logs_list.filter(status='Sent').count()
    failed_sms = sms_logs_list.filter(status='Failed').count()
    pending_sms = sms_logs_list.filter(status='Pending').count()
    
    # Pagination - 20 items per page
    paginator = Paginator(sms_logs_list, 20)
    page = request.GET.get('page', 1)
    
    try:
        sms_logs = paginator.page(page)
    except PageNotAnInteger:
        sms_logs = paginator.page(1)
    except EmptyPage:
        sms_logs = paginator.page(paginator.num_pages)
    
    context = {
        'sms_logs': sms_logs,
        'total_sms': total_sms,
        'successful_sms': successful_sms,
        'failed_sms': failed_sms,
        'pending_sms': pending_sms,
    }
    
    return render(request, 'admin_sms_logs.html', context)