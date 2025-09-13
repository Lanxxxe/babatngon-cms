from admins.models import Complaint, AssistanceRequest, ComplaintAttachment, AssistanceAttachment
from admins.notification_utils import notify_new_case_filed
from core.models import User
from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect, get_object_or_404
from django.db import IntegrityError
from django.http import JsonResponse
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os, uuid, time
import sweetify



# Create your views here.
def resident_dashboard(request):
    if not request.session.get('id'):
        sweetify.error(request, 'You must be logged in to access the dashboard.', timer=3000)
        return redirect('homepage')
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
        return redirect('homepage')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        other_category = request.POST.get('other_category', '').strip()
        priority = request.POST.get('priority', 'low')
        location_description = request.POST.get('location', '').strip()
        address = request.POST.get('address', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        user_id = request.session.get('id')
        user = User.objects.filter(id=user_id).first()
        
        # Validate required fields
        if not all([title, description, category]):
            sweetify.error(request, 'Please fill in all required fields.', persistent=True, timer=3000)
            return render(request, 'file_complaint.html')
        
        # If "Others" is selected, validate that other_category is provided
        if category == 'Others' and not other_category:
            sweetify.error(request, 'Please specify the other category.', persistent=True, timer=3000)
            return render(request, 'file_complaint.html')
        
        # Use the specified other category if "Others" is selected
        final_category = other_category if category == 'Others' else category
        
        # Convert coordinates to float if provided, otherwise set to None
        try:
            lat_float = float(latitude) if latitude else None
            lng_float = float(longitude) if longitude else None
        except (ValueError, TypeError):
            lat_float = None
            lng_float = None
        
        complaint = Complaint.objects.create(
            user=user,
            title=title,
            description=description,
            category=final_category,
            priority=priority,
            location_description=location_description,
            address=address,
            latitude=lat_float,
            longitude=lng_float
        )

        try:
            notify_new_case_filed(complaint)  # Notifies all active admins
        
        except Exception as e:
            # Log the error but do not interrupt the user flow
            print(f"Error notifying admins of new complaint: {e}")
            sweetify.error(request, 'There was an error notifying admins. Please try again later.', persistent=True, timer=3000)

        # Handle multiple file uploads - let Django handle the file saving
        for f in request.FILES.getlist('attachments'):
            ComplaintAttachment.objects.create(complaint=complaint, file=f)

        sweetify.success(request, 'Complaint filed successfully!', persistent=True, timer=3000)
        return redirect('file_complaint')
    return render(request, 'file_complaint.html')


def file_assistance(request):
    if not request.session.get('id'):
        sweetify.error(request, 'You must be logged in to request assistance.', persistent=True, timer=3000)
        return redirect('homepage')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        type_ = request.POST.get('type', '').strip()
        other_assistance_type = request.POST.get('other_assistance_type', '').strip()
        urgency = request.POST.get('urgency', 'low')
        address = request.POST.get('address', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        user_id = request.session.get('id')
        user = User.objects.filter(id=user_id).first()
        
        # Validate required fields
        if not all([title, description, type_]):
            sweetify.error(request, 'Please fill in all required fields.', persistent=True, timer=3000)
            return render(request, 'file_assistance.html')
        
        # If "Others" is selected, validate that other_assistance_type is provided
        if type_ == 'Others' and not other_assistance_type:
            sweetify.error(request, 'Please specify the other assistance type.', persistent=True, timer=3000)
            return render(request, 'file_assistance.html')
        
        # Use the specified other assistance type if "Others" is selected
        final_type = other_assistance_type if type_ == 'Others' else type_
        
        # Convert coordinates to float if provided, otherwise set to None
        try:
            lat_float = float(latitude) if latitude else None
            lng_float = float(longitude) if longitude else None
        except (ValueError, TypeError):
            lat_float = None
            lng_float = None
        
        assistance = AssistanceRequest.objects.create(
            user=user,
            title=title,
            description=description,
            type=final_type,
            urgency=urgency,
            address=address,
            latitude=lat_float,
            longitude=lng_float
        )

        try:
            notify_new_case_filed(assistance)  # Notifies all active admins
        except Exception as e:
            print(f"Error notifying admins of new assistance request: {e}")
            sweetify.error(request, 'There was an error notifying admins. Please try again later.', persistent=True, timer=3000)

        # Handle multiple file uploads - let Django handle the file saving
        for f in request.FILES.getlist('attachments'):
            AssistanceAttachment.objects.create(assistance=assistance, file=f)
        sweetify.success(request, 'Assistance request submitted!', persistent=True, timer=3000)
        return redirect('file_assistance')
    return render(request, 'file_assistance.html')


def my_complaints(request):
    if not request.session.get('id'):
        sweetify.error(request, 'You must be logged in to view your complaints.', persistent=True, timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('id')
    user = User.objects.filter(id=user_id).first()
    complaints = Complaint.objects.filter(user=user).order_by('-created_at')
    return render(request, 'my_complaints.html', {'complaints': complaints})


def delete_complaint(request, pk):
    user_id = request.session.get('id')
    complaint = get_object_or_404(Complaint, pk=pk, user_id=user_id)
    complaint.delete()
    sweetify.success(request, 'Complaint deleted.', persistent=True, timer=2000)
    return redirect('my_complaints')


def update_complaint(request, pk):
    user_id = request.session.get('id')
    complaint = get_object_or_404(Complaint, pk=pk, user_id=user_id)
    if request.method == 'POST':
        complaint.title = request.POST.get('title', complaint.title)
        complaint.description = request.POST.get('description', complaint.description)
        complaint.category = request.POST.get('category', complaint.category)
        complaint.priority = request.POST.get('priority', complaint.priority)
        complaint.location_description = request.POST.get('location', complaint.location_description)
        complaint.address = request.POST.get('address', complaint.address)
        
        # Handle coordinate updates
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        
        try:
            complaint.latitude = float(latitude) if latitude else complaint.latitude
            complaint.longitude = float(longitude) if longitude else complaint.longitude
        except (ValueError, TypeError):
            # Keep existing coordinates if invalid input
            pass
        
        # Handle attachment deletions
        attachments_to_delete = request.POST.getlist('delete_attachments')
        if attachments_to_delete:
            for attachment_id in attachments_to_delete:
                try:
                    attachment = ComplaintAttachment.objects.get(id=attachment_id, complaint=complaint)
                    # Delete the file from storage
                    if attachment.file and os.path.exists(attachment.file.path):
                        os.remove(attachment.file.path)
                    attachment.delete()
                except ComplaintAttachment.DoesNotExist:
                    pass
        
        # Handle new file uploads
        new_files = request.FILES.getlist('new_attachments')
        for file in new_files:
            ComplaintAttachment.objects.create(complaint=complaint, file=file)
        
        complaint.save()
        sweetify.success(request, 'Complaint updated successfully.', persistent=True, timer=2000)
        return redirect('my_complaints')
    
    # For AJAX/modal prefill
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Get attachments for the complaint
        attachments = []
        for attachment in complaint.attachments.all():
            attachments.append({
                'id': attachment.id,
                'file_name': attachment.file.name.split('/')[-1],  # Get just the filename
                'file_url': attachment.file.url,
                'uploaded_at': attachment.uploaded_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            'id': complaint.id,
            'title': complaint.title,
            'description': complaint.description,
            'category': complaint.category,
            'priority': complaint.priority,
            'location': complaint.location_description,
            'address': complaint.address,
            'latitude': float(complaint.latitude) if complaint.latitude else None,
            'longitude': float(complaint.longitude) if complaint.longitude else None,
            'status': complaint.status,
            'created_at': complaint.created_at.strftime('%Y-%m-%d %H:%M'),
            'attachments': attachments,
        })
    return redirect('my_complaints')


def my_assistance(request):
    if not request.session.get('id'):
        sweetify.error(request, 'You must be logged in to view your assistance requests.', timer=3000)
        return redirect('homepage')
    user_id = request.session.get('id')
    user = User.objects.filter(id=user_id).first()
    assistance_list = AssistanceRequest.objects.filter(user=user).order_by('-created_at')

    context = {
        'assistance_list': assistance_list,
    }

    return render(request, 'my_assistance.html', context)


def update_assistance(request, pk):
    user_id = request.session.get('id')
    assistance = get_object_or_404(AssistanceRequest, pk=pk, user_id=user_id)
    if request.method == 'POST':
        assistance.title = request.POST.get('title', assistance.title)
        assistance.description = request.POST.get('description', assistance.description)
        type_ = request.POST.get('type', assistance.type)
        other_assistance_type = request.POST.get('other_assistance_type', '').strip()
        assistance.urgency = request.POST.get('urgency', assistance.urgency)
        assistance.address = request.POST.get('address', assistance.address)
        
        # Handle "Others" assistance type
        if type_ == 'Others' and other_assistance_type:
            assistance.type = other_assistance_type
        elif type_ != 'Others':
            assistance.type = type_
        
        # Handle coordinate updates
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        
        try:
            assistance.latitude = float(latitude) if latitude else assistance.latitude
            assistance.longitude = float(longitude) if longitude else assistance.longitude
        except (ValueError, TypeError):
            # Keep existing coordinates if invalid input
            pass
        
        # Handle attachment deletions
        attachments_to_delete = request.POST.getlist('delete_attachments')
        if attachments_to_delete:
            for attachment_id in attachments_to_delete:
                try:
                    attachment = AssistanceAttachment.objects.get(id=attachment_id, assistance=assistance)
                    # Delete the physical file
                    if attachment.file and os.path.exists(attachment.file.path):
                        os.remove(attachment.file.path)
                    attachment.delete()
                except AssistanceAttachment.DoesNotExist:
                    pass  # Attachment doesn't exist, skip
        
        # Handle new file uploads
        new_files = request.FILES.getlist('new_attachments')
        for file in new_files:
            AssistanceAttachment.objects.create(assistance=assistance, file=file)
        
        assistance.save()
        sweetify.success(request, 'Assistance updated.', persistent=True, timer=2000)
        return redirect('my_assistance')
    # For AJAX/modal prefill
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Get attachments for the assistance request
        attachments = []
        for attachment in assistance.attachments.all():
            attachments.append({
                'id': attachment.id,
                'file_name': attachment.file.name.split('/')[-1],  # Get just the filename
                'file_url': attachment.file.url,
                'uploaded_at': attachment.uploaded_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            'id': assistance.id,
            'title': assistance.title,
            'description': assistance.description,
            'type': assistance.type,
            'urgency': assistance.urgency,
            'status': assistance.status,
            'address': assistance.address,
            'latitude': float(assistance.latitude) if assistance.latitude else None,
            'longitude': float(assistance.longitude) if assistance.longitude else None,
            'created_at': assistance.created_at.strftime('%Y-%m-%d %H:%M'),
            'attachments': attachments,
        })
    return redirect('my_assistance')


def delete_assistance(request, pk):
    user_id = request.session.get('id')
    assistance = get_object_or_404(AssistanceRequest, pk=pk, user_id=user_id)
    assistance.delete()
    sweetify.success(request, 'Assistance request deleted.', persistent=True, timer=2000)
    return redirect('my_assistance')


def profile(request):
    """
    Resident profile page: view info, upload profile picture, update password.
    """
    user_id = request.session.get('id')
    user = User.objects.filter(id=user_id).first()
    
    if not user:
        sweetify.error(request, 'You must be logged in to view your profile.', timer=3000)
        return redirect('homepage')

    if request.method == 'POST':
        # Handle profile picture upload
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            file_upload_view.handle_profile_picture_upload(request, user, profile_picture)
            sweetify.success(request, 'Profile picture updated.', persistent=True, timer=2000)

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

