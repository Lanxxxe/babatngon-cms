from core.models import User
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse
from admins.notification_utils import notify_new_case_filed
from admins.models import Complaint, ComplaintAttachment, Notification
from resident.automate_priority import generate_priority, prompt_details
import os
import sweetify

# Complaint Views
def file_complaint(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to file a complaint.', timer=3000)
        return redirect('homepage')
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        other_category = request.POST.get('other_category', '').strip()
        # priority = request.POST.get('priority', 'low')
        location_description = request.POST.get('location', '').strip()
        address = request.POST.get('address', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        user_id = request.session.get('resident_id')
        user = User.objects.filter(id=user_id).first()
        
        # Validate required fields
        if not all([title, description, category, location_description, address]):
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

        
        complaint_details = {
            'subject': title,
            'description': description,
            'category': final_category,
            'location_description': location_description,
            'address': address,
        }
        
        details = prompt_details(complaint_details)

        priority = generate_priority(details).lower()
        
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


def my_complaints(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to view your complaints.', persistent=True, timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    complaints = Complaint.objects.filter(user=user).order_by('-created_at')
    return render(request, 'my_complaints.html', {'complaints': complaints})


def complaint_details(request, pk):
    user_id = request.session.get('resident_id')

    if not user_id:
        sweetify.error(request, 'You must be logged in to view complaint details.', persistent=True, timer=3000)
        return redirect('homepage')

    user = User.objects.filter(id=user_id).first()
    complaint = get_object_or_404(Complaint, pk=pk, user=user)
    attachments = ComplaintAttachment.objects.filter(complaint=complaint)

    context = {
        'complaint': complaint,
        'attachments': attachments,
    }

    return render(request, 'complaint_details/view_complaint_details.html', context)


def delete_complaint(request, pk):

    user_id = request.session.get('resident_id')
    if not user_id:
        sweetify.error(request, 'You must be logged in to delete a complaint.', persistent=True, timer=3000)
        return redirect('homepage')

    complaint = get_object_or_404(Complaint, pk=pk, user_id=user_id)
    complaint.delete()
    sweetify.success(request, 'Complaint deleted.', persistent=True, timer=2000)
    return redirect('my_complaints')


def update_complaint(request, pk):
    user_id = request.session.get('resident_id')
    if not user_id:
        sweetify.error(request, 'Action not allowed.', persistent=True, timer=3000)
        return redirect('homepage')
    
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


def follow_up_complaint(request, complaint_id):
    """Handle follow-up on a complaint by creating admin notifications."""
    
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in.', timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    complaint = get_object_or_404(Complaint, id=complaint_id, user=user)
    
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()

        complaint_details = {
            'subject': complaint.title,
            'description': complaint.description,
            'category': complaint.category,
            'location_description': complaint.location_description,
            'address': complaint.address,
            'follow_up_message': message
        }
        
        details = prompt_details(complaint_details, is_follow_up=True)

        priority = generate_priority(details).lower()
        

        if not message:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Follow-up message is required.'})
            sweetify.error(request, 'Follow-up message is required.', timer=3000)
            return redirect('my_complaints')
        
        try:

            # Use the unified notification system to notify all admins
            notifications = Notification.notify_admins(
                sender=user,
                title=f'Follow-up on Complaint #{complaint.id}: {complaint.title}',
                message=f'Resident {user.get_full_name()} has sent a follow-up message:\n\n{message}\n\nComplaint Details:\n- Title: {complaint.title}\n- Category: {complaint.category}\n- Status: {complaint.status.replace("_", " ").title()}\n- Priority: {complaint.priority.title()}\n- Filed: {complaint.created_at.strftime("%B %d, %Y at %I:%M %p")}',
                notification_type='status_update',
                action_type='commented',
                priority=priority,
                related_complaint=complaint
            )

            notifications_created = len(notifications)

            complaint.priority = priority
            complaint.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': f'Follow-up sent successfully to {notifications_created} administrator(s)!'
                })
            
            sweetify.success(request, f'Follow-up sent successfully to {notifications_created} administrator(s)!', timer=3000)
            return redirect('my_complaints')
            
        except Exception as e:
            print(f"Error creating follow-up notification: {e}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Error sending follow-up. Please try again.'})
            sweetify.error(request, 'Error sending follow-up. Please try again.', timer=3000)
            return redirect('my_complaints')
    
    # If GET request, redirect to complaints page
    return redirect('my_complaints')

