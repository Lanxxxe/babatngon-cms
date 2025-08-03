from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.db import IntegrityError
from core.models import User
from admins.models import Complaint, AssistanceRequest, ComplaintAttachment, AssistanceAttachment
import sweetify


# Create your views here.
def resident_dashboard(request):
    user_id = request.session.get('id')
    user = User.objects.filter(id=user_id).first()

    # Complaints stats
    total_complaints = Complaint.objects.filter(user=user).count()
    pending_complaints = Complaint.objects.filter(user=user, status='pending').count()
    in_progress_complaints = Complaint.objects.filter(user=user, status='in_progress').count()
    resolved_complaints = Complaint.objects.filter(user=user, status='resolved').count()
    recent_complaints = Complaint.objects.filter(user=user).order_by('-created_at')[:5]

    # Assistance stats
    total_assistance = AssistanceRequest.objects.filter(user=user).count()
    pending_assistance = AssistanceRequest.objects.filter(user=user, status='pending').count()
    in_progress_assistance = AssistanceRequest.objects.filter(user=user, status='in_progress').count()
    completed_assistance = AssistanceRequest.objects.filter(user=user, status='completed').count()
    recent_assistance = AssistanceRequest.objects.filter(user=user).order_by('-created_at')[:5]

    context = {
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
        'recent_complaints': recent_complaints,
        'total_assistance': total_assistance,
        'pending_assistance': pending_assistance,
        'in_progress_assistance': in_progress_assistance,
        'completed_assistance': completed_assistance,
        'recent_assistance': recent_assistance,
    }
    return render(request, 'resident_dashboard.html', context)

def file_complaint(request):
    if not request.session.get('id'):
        sweetify.error(request, 'You must be logged in to file a complaint.', timer=3000)
        return redirect('login')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        priority = request.POST.get('priority', 'low')
        location = request.POST.get('location', '').strip()
        user_id = request.session.get('id')
        user = User.objects.filter(id=user_id).first()
        if not all([title, description, category]):
            sweetify.error(request, 'Please fill in all required fields.', timer=3000)
            return render(request, 'file_complaint.html')
        
        complaint = Complaint.objects.create(
            user=user,
            title=title,
            description=description,
            category=category,
            priority=priority,
            location=location
        )
        # Handle multiple file uploads
        for f in request.FILES.getlist('attachments'):
            ComplaintAttachment.objects.create(complaint=complaint, file=f)

        sweetify.success(request, 'Complaint filed successfully!', timer=3000)
        return redirect('resident_dashboard')
    return render(request, 'file_complaint.html')

def file_assistance(request):
    if not request.session.get('id'):
        sweetify.error(request, 'You must be logged in to request assistance.', timer=3000)
        return redirect('login')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        type_ = request.POST.get('type', '').strip()
        urgency = request.POST.get('urgency', 'low')
        user_id = request.session.get('id')
        user = User.objects.filter(id=user_id).first()
        if not all([title, description, type_]):
            sweetify.error(request, 'Please fill in all required fields.', timer=3000)
            return render(request, 'file_assistance.html')
        assistance = AssistanceRequest.objects.create(
            user=user,
            title=title,
            description=description,
            type=type_,
            urgency=urgency
        )
        # Handle multiple file uploads
        for f in request.FILES.getlist('attachments'):
            AssistanceAttachment.objects.create(assistance=assistance, file=f)
        sweetify.success(request, 'Assistance request submitted!', timer=3000)
        return redirect('resident_dashboard')
    return render(request, 'file_assistance.html')


def resident_logout(request):
    logout(request)
    sweetify.success(request, 'You have been logged out successfully.', timer=3000)
    return redirect('homepage')