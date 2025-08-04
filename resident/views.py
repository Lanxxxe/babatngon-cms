from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect, get_object_or_404
from django.db import IntegrityError
from django.http import JsonResponse
from core.models import User
from admins.models import Complaint, AssistanceRequest, ComplaintAttachment, AssistanceAttachment
import sweetify

from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os


# Utility function for handling profile picture upload
def handle_profile_picture_upload(user, uploaded_file):
    """
    Handles saving the uploaded profile picture for the user.
    Deletes the old picture if it exists.
    """
    if not uploaded_file:
        return
    # Save to uploads/profile_pictures/<user_id>_<filename>
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'profile_pictures')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{user.id}_{uploaded_file.name}"
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    # Remove old picture if exists and is not default
    if user.profile_picture and os.path.exists(user.profile_picture.path):
        try:
            os.remove(user.profile_picture.path)
        except Exception:
            pass
    # Update user profile_picture field
    user.profile_picture = f"profile_pictures/{filename}"
    user.save()


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

def my_complaints(request):
    user_id = request.session.get('id')
    user = User.objects.filter(id=user_id).first()
    complaints = Complaint.objects.filter(user=user).order_by('-created_at')
    return render(request, 'my_complaints.html', {'complaints': complaints})

def delete_complaint(request, pk):
    user_id = request.session.get('id')
    complaint = get_object_or_404(Complaint, pk=pk, user_id=user_id)
    complaint.delete()
    sweetify.success(request, 'Complaint deleted.', timer=2000)
    return redirect('my_complaints')

def update_complaint(request, pk):
    user_id = request.session.get('id')
    complaint = get_object_or_404(Complaint, pk=pk, user_id=user_id)
    if request.method == 'POST':
        complaint.title = request.POST.get('title', complaint.title)
        complaint.description = request.POST.get('description', complaint.description)
        complaint.category = request.POST.get('category', complaint.category)
        complaint.priority = request.POST.get('priority', complaint.priority)
        complaint.location = request.POST.get('location', complaint.location)
        complaint.save()
        sweetify.success(request, 'Complaint updated.', timer=2000)
        return redirect('my_complaints')
    # For AJAX/modal prefill
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'id': complaint.id,
            'title': complaint.title,
            'description': complaint.description,
            'category': complaint.category,
            'priority': complaint.priority,
            'location': complaint.location,
            'status': complaint.status,
            'created_at': complaint.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    return redirect('my_complaints')


def my_assistance(request):
    user_id = request.session.get('id')
    user = User.objects.filter(id=user_id).first()
    assistance_list = AssistanceRequest.objects.filter(user=user).order_by('-created_at')
    return render(request, 'my_assistance.html', {'assistance_list': assistance_list})

def update_assistance(request, pk):
    user_id = request.session.get('id')
    assistance = get_object_or_404(AssistanceRequest, pk=pk, user_id=user_id)
    if request.method == 'POST':
        assistance.title = request.POST.get('title', assistance.title)
        assistance.description = request.POST.get('description', assistance.description)
        assistance.type = request.POST.get('type', assistance.type)
        assistance.urgency = request.POST.get('urgency', assistance.urgency)
        assistance.save()
        sweetify.success(request, 'Assistance updated.', timer=2000)
        return redirect('my_assistance')
    # For AJAX/modal prefill
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'id': assistance.id,
            'title': assistance.title,
            'description': assistance.description,
            'type': assistance.type,
            'urgency': assistance.urgency,
            'status': assistance.status,
            'created_at': assistance.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    return redirect('my_assistance')

def delete_assistance(request, pk):
    user_id = request.session.get('id')
    assistance = get_object_or_404(AssistanceRequest, pk=pk, user_id=user_id)
    assistance.delete()
    sweetify.success(request, 'Assistance request deleted.', timer=2000)
    return redirect('my_assistance')

def profile(request):
    """
    Resident profile page: view info, upload profile picture, update password.
    """
    user_id = request.session.get('id')
    user = User.objects.filter(id=user_id).first()
    if not user:
        sweetify.error(request, 'You must be logged in to view your profile.', timer=3000)
        return redirect('login')

    if request.method == 'POST':
        # Handle profile picture upload
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            handle_profile_picture_upload(user, profile_picture)
            sweetify.success(request, 'Profile picture updated.', timer=2000)

        # Handle password change
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        if current_password or new_password or confirm_password:
            if not (current_password and new_password and confirm_password):
                sweetify.error(request, 'Please fill in all password fields.', timer=3000)
            elif not check_password(current_password, user.password):
                sweetify.error(request, 'Current password is incorrect.', timer=3000)
            elif new_password != confirm_password:
                sweetify.error(request, 'New passwords do not match.', timer=3000)
            elif len(new_password) < 6:
                sweetify.error(request, 'New password must be at least 6 characters.', timer=3000)
            else:
                user.password = make_password(new_password)
                user.save()
                sweetify.success(request, 'Password updated successfully.', timer=2000)
        return redirect('profile')

    context = {
        'user': user,
    }
    return render(request, 'profile.html', context)




def resident_logout(request):
    logout(request)
    sweetify.toast(request, 'You have been logged out successfully.', timer=3000)
    return redirect('homepage')

