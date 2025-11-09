from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse
from admins.notification_utils import notify_new_case_filed
from admins.models import AssistanceRequest, AssistanceAttachment
from admins.models import Notification
from resident.automate_priority import generate_priority, prompt_details
from core.models import User
import os, sweetify



# Assistance Views
def file_assistance(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to request assistance.', persistent=True, timer=3000)
        return redirect('homepage')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        type_ = request.POST.get('type', '').strip()
        other_assistance_type = request.POST.get('other_assistance_type', '').strip()
        # urgency = request.POST.get('urgency', 'low')
        address = request.POST.get('address', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        user_id = request.session.get('resident_id')
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
        
        assistance_details = {
            'subject' : title,
            'description' : description,
            'type' : final_type,
            'address' : address,
        }

        details = prompt_details(assistance_details)
        priority = generate_priority(details).lower()

        assistance = AssistanceRequest.objects.create(
            user=user,
            title=title,
            description=description,
            type=final_type,
            urgency=priority,
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


def my_assistance(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to view your assistance requests.', timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    assistance_list = AssistanceRequest.objects.filter(user=user).order_by('-created_at')

    context = {
        'assistance_list': assistance_list,
    }

    return render(request, 'my_assistance.html', context)


def assistance_detail(request, pk):
    user_id = request.session.get('resident_id')
    if not user_id:
        sweetify.error(request, 'Action not allowed.', persistent="Okay", timer=3000)
        return redirect('homepage')
    
    user = User.objects.filter(id=user_id).first()
    assistance = get_object_or_404(AssistanceRequest, pk=pk, user=user)
    attachments = AssistanceAttachment.objects.filter(assistance=assistance)
    context = {
        'assistance': assistance,
        'attachments': attachments,
    }

    return render(request, 'assistance_details/view_assistance_details.html', context)


def update_assistance(request, pk):
    user_id = request.session.get('resident_id')
    if not user_id:
        sweetify.error(request, 'Action not allowed.', persistent="Okay", timer=3000)
        return redirect('homepage')
    assistance = get_object_or_404(AssistanceRequest, pk=pk, user_id=user_id)

    if request.method == 'POST':
        subject = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        assistance_type = request.POST.get('type', '').strip()
        other_assistance_type = request.POST.get('other_assistance_type', '').strip()
        address = request.POST.get('address', '').strip()
        # Handle coordinate updates
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()

        # Handle "Others" assistance type
        if assistance_type == 'Others' and other_assistance_type:
            assistance.type = other_assistance_type

        # Handle attachment deletions
        attachments_to_delete = request.POST.getlist('delete_attachments')
        if attachments_to_delete:
            for attachment_id in attachments_to_delete:
                try:
                    attachment = AssistanceAttachment.objects.get(id=attachment_id, assistance=assistance)
                    attachment.delete()
                except AssistanceAttachment.DoesNotExist:
                    continue
        
        details = {
            'subject' : subject if subject else assistance.title,
            'description' : description if description else assistance.description,
            'type' : assistance_type if assistance_type != 'Others' else assistance.type,
            'address' : address if address else assistance.address,
        }

        detail_prompt = prompt_details(details)
        priority = generate_priority(detail_prompt).lower()

        try:
            assistance.title = subject if subject else assistance.title
            assistance.description = description if description else assistance.description
            assistance.type = assistance_type if assistance_type != 'Others' else assistance.type
            assistance.address = address if address else assistance.address
            assistance.urgency = priority
        
            try:
                assistance.latitude = float(latitude) if latitude else assistance.latitude
                assistance.longitude = float(longitude) if longitude else assistance.longitude
            except (ValueError, TypeError):
                # Keep existing coordinates if invalid input
                pass

            # Handle new file uploads
            new_files = request.FILES.getlist('new_attachments')
            for file in new_files:
                AssistanceAttachment.objects.create(assistance=assistance, file=file)

            assistance.save()

            sweetify.success(request, 'Assistance updated.', persistent="Okay", timer=2000)
            return redirect('my_assistance')


        except Exception:
            sweetify.error(request, 'Error updating assistance details.', persistent="Okay", timer=3000)
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
    user_id = request.session.get('resident_id')
    if not user_id:
        sweetify.error(request, 'Action not allowed', persistent="Okay", timer=3000)
        return redirect('homepage')
    assistance = get_object_or_404(AssistanceRequest, pk=pk, user_id=user_id)
    assistance.delete()
    sweetify.success(request, 'Assistance request deleted.', persistent=True, timer=2000)
    return redirect('my_assistance')


def follow_up_assistance(request, assistance_id):
    """Handle follow-up on an assistance request by creating admin notifications."""
    if not request.session.get('resident_id'):
        sweetify.error(request, 'Action not allowed.', persistent="Okay", timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    assistance = get_object_or_404(AssistanceRequest, id=assistance_id, user=user)
    
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        # urgency = request.POST.get('urgency', 'normal')
        
        assistance_details = {
            'subject' : assistance.title,
            'description' : assistance.description,
            'type' : assistance.type,
            'address' : assistance.address,
            'follow_up_message' : message,
        }

        details = prompt_details(assistance_details)
        priority = generate_priority(details)
        
        if not message:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Follow-up message is required.'})
            sweetify.error(request, 'Follow-up message is required.', timer=3000)
            return redirect('my_assistance')
        
        try:
            
            # Use the unified notification system to notify all admins
            notifications = Notification.notify_admins(
                sender=user,
                title=f'Follow-up on Assistance Request #{assistance.id}: {assistance.title}',
                message=f'Resident {user.get_full_name()} has sent a follow-up message:\n\n{message}\n\nAssistance Request Details:\n- Title: {assistance.title}\n- Type: {assistance.type}\n- Status: {assistance.status.replace("_", " ").title()}\n- Urgency: {assistance.urgency.title()}\n- Filed: {assistance.created_at.strftime("%B %d, %Y at %I:%M %p")}',
                notification_type='new_assistance',
                action_type='commented',
                priority=priority,
                related_assistance=assistance
            )

            notifications_created = len(notifications)

            assistance.urgency = priority
            assistance.save()    


            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': f'Follow-up sent successfully to {notifications_created} administrator(s)!'
                })
            
            sweetify.success(request, f'Follow-up sent successfully to {notifications_created} administrator(s)!', timer=3000)
            return redirect('my_assistance')
            
        except Exception as e:
            print(f"Error creating assistance follow-up notification: {e}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Error sending follow-up. Please try again.'})
            sweetify.error(request, 'Error sending follow-up. Please try again.', timer=3000)
            return redirect('my_assistance')
    
    # If GET request, redirect to assistance page
    return redirect('my_assistance')




