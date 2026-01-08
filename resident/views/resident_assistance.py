from django.shortcuts import redirect, get_object_or_404, render
from core.models import User
from django.http import JsonResponse
from admins.models import Notification
from admins.models import AssistanceRequest, AssistanceAttachment
from admins.notification_utils import notify_new_case_filed
from resident.automate_priority import generate_priority, prompt_details
from admins.user_activity_utils import log_case_activity, log_activity
from core.sms_util import send_sms, format_emergency_alert, format_assistance_notification, follow_up_request
from core.models import StaffAdmin
import sweetify


# Emergency Assistance View
def file_emergency_assistance(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to request emergency assistance.', timer=3000)
        return redirect('homepage')
    
    if request.method == 'POST':
        title = request.POST.get('title', 'Emergency Assistance Required - Immediate Help Needed').strip()
        description = request.POST.get('description', '').strip()
        type_ = 'Emergency'  # Fixed type for emergency assistance
        urgency = 'urgent'  # Fixed urgency for emergency assistance
        address = request.POST.get('address', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        user_id = request.session.get('resident_id')
        user = User.objects.filter(id=user_id).first()
        
        # Validate required fields
        if not all([title, description, address, latitude, longitude]):
            sweetify.error(request, 'Please fill in all required fields and pin the location on the map.', persistent=True, timer=3000)
            return render(request, 'emergency_assistance.html')
        
        # Convert coordinates to float
        try:
            lat_float = float(latitude)
            lng_float = float(longitude)
        except (ValueError, TypeError):
            sweetify.error(request, 'Invalid coordinates. Please pin a location on the map.', persistent=True, timer=3000)
            return render(request, 'emergency_assistance.html')

        # Create the emergency assistance request
        assistance = AssistanceRequest.objects.create(
            user=user,
            title=title,
            description=description,
            type=type_,
            urgency=urgency,
            address=address,
            latitude=lat_float,
            longitude=lng_float
        )

        emergency_formatted_message = format_emergency_alert(
            f"Emergency Message Received:\n\n"
            f"Emergency Assistance Request #{assistance.id} filed by {user.get_full_name()}\n"
            f"Subject: {assistance.title}\n"
            f"Description: {assistance.description}\n"
            f"Location: {assistance.address}\n"
            f"Priority: URGENT"
        )


        if user.phone is not None or user.phone != '':
            send_sms(user.phone, emergency_formatted_message)

        admins = StaffAdmin.objects.filter(is_active=True, role="admin")

        for admin in admins:
            admin_message = format_emergency_alert(
                f"New Emergency Assistance Request #{assistance.id} filed by {user.get_full_name()}\n"
                f"Subject: {assistance.title}\n"
                f"Description: {assistance.description}\n"
                f"Location: {assistance.address}\n"
                f"Priority: URGENT"
            )
            
            if admin.phone_number is not None or admin.phone_number != '':
                send_sms(admin.phone_number, admin_message)

        try:
            notify_new_case_filed(assistance)  # Notifies all active admins
        except Exception as e:
            # Log the error but do not interrupt the user flow
            pass
        # Handle multiple file uploads
        for f in request.FILES.getlist('attachments'):
            AssistanceAttachment.objects.create(assistance=assistance, file=f)


        # Log activity
        log_case_activity(
            user=user,
            case=assistance,
            activity_type='assistance_filed',
            description=f'{user.get_full_name()} filed emergency assistance request #{assistance.id}: {assistance.title}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'type': assistance.type, 'urgency': assistance.urgency, 'request_type': 'emergency'}
        )

        sweetify.success(request, 'Emergency assistance request filed successfully! Admins have been notified.', persistent=True, timer=3000)
        return redirect('my_assistance')
    
    return render(request, 'emergency_assistance.html')


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

        assistance_details = format_assistance_notification(
            assistance_id=assistance.id,
            title=assistance.title,
            status=assistance.status.replace('_', ' ')
        )

        if user.phone is not None or user.phone != '':
            send_sms(user.phone, assistance_details)

        for admin in StaffAdmin.objects.filter(is_active=True, role="admin"):
            if admin.phone_number is not None or admin.phone_number != '':
                send_sms(admin.phone_number, assistance_details)

        try:
            notify_new_case_filed(assistance)  # Notifies all active admins
        except Exception as e:
            sweetify.error(request, 'There was an error notifying admins. Please try again later.', persistent=True, timer=3000)

        # Handle multiple file uploads - let Django handle the file saving
        for f in request.FILES.getlist('attachments'):
            AssistanceAttachment.objects.create(assistance=assistance, file=f)
        
        # Log activity
        log_case_activity(
            user=user,
            case=assistance,
            activity_type='assistance_filed',
            description=f'{user.get_full_name()} filed assistance request #{assistance.id}: {assistance.title}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'type': assistance.type, 'urgency': assistance.urgency}
        )
        
        sweetify.success(request, 'Assistance request submitted!', persistent=True, timer=3000)
        return redirect('file_assistance')
    return render(request, 'file_assistance.html')


def my_assistance(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to view your assistance requests.', timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    
    # Get all assistance requests for the user
    assistance_list = AssistanceRequest.objects.filter(user=user).order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    urgency_filter = request.GET.get('urgency')
    search_query = request.GET.get('search')
    
    if status_filter:
        assistance_list = assistance_list.filter(status=status_filter)
    
    if urgency_filter:
        assistance_list = assistance_list.filter(urgency=urgency_filter)
    
    if search_query:
        from django.db.models import Q
        assistance_list = assistance_list.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    # Log activity
    filter_info = []
    if status_filter:
        filter_info.append(f"status: {status_filter}")
    if urgency_filter:
        filter_info.append(f"urgency: {urgency_filter}")
    if search_query:
        filter_info.append(f"search: '{search_query}'")
    filter_desc = f" with filters ({', '.join(filter_info)})" if filter_info else ""
    
    log_activity(
        user=user,
        activity_type='assistance_viewed',
        activity_category='case_management',
        description=f'{user.get_full_name()} viewed their assistance requests{filter_desc}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        metadata={'total_assistance': assistance_list.count(), 'filters': {'status': status_filter, 'urgency': urgency_filter, 'search': search_query}}
    )

    context = {
        'assistance_list': assistance_list,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'search_query': search_query,
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
    
    # Log activity
    log_case_activity(
        user=user,
        case=assistance,
        activity_type='assistance_viewed',
        description=f'{user.get_full_name()} viewed assistance request #{assistance.id} details: {assistance.title}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        metadata={'status': assistance.status, 'urgency': assistance.urgency}
    )
    
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

            # Log activity
            user = User.objects.filter(id=user_id).first()
            log_case_activity(
                user=user,
                case=assistance,
                activity_type='assistance_updated',
                description=f'{user.get_full_name()} updated assistance request #{assistance.id}: {assistance.title}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'type': assistance.type, 'urgency': assistance.urgency}
            )

            sweetify.success(request, 'Assistance updated.', persistent="Okay", timer=2000)
            return redirect('my_assistance')


        except Exception as e:
            user = User.objects.filter(id=user_id).first()
            if user:
                log_activity(
                    user=user,
                    activity_type='assistance_updated',
                    activity_category='case_management',
                    description=f'{user.get_full_name()} failed to update assistance request',
                    is_successful=False,
                    error_message=str(e),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
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
    user = User.objects.filter(id=user_id).first()
    
    # Store info before deletion
    assistance_title = assistance.title
    assistance_id = assistance.id
    
    assistance.delete()
    
    # Log activity
    if user:
        log_activity(
            user=user,
            activity_type='assistance_deleted',
            activity_category='case_management',
            description=f'{user.get_full_name()} deleted assistance request #{assistance_id}: {assistance_title}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'assistance_id': assistance_id, 'assistance_title': assistance_title}
        )
    
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

            message_format = follow_up_request(
                case_id=assistance.id,
                subject=assistance.title,
                status=assistance.status.replace('_', ' ').title()
            )

            for admin in StaffAdmin.objects.filter(is_active=True, role="admin"):
                if admin.phone_number is not None or admin.phone_number != '':
                    send_sms(admin.phone_number, message_format)
            # Log activity
            log_case_activity(
                user=user,
                case=assistance,
                activity_type='followup_request',
                description=f'{user.get_full_name()} sent follow-up for assistance request #{assistance.id}: {assistance.title}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'notifications_sent': notifications_created, 'message_length': len(message), 'priority': priority}
            )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': f'Follow-up sent successfully to {notifications_created} administrator(s)!'
                })
            
            sweetify.success(request, f'Follow-up sent successfully to {notifications_created} administrator(s)!', timer=3000)
            return redirect('my_assistance')
            
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Error sending follow-up. Please try again.'})
            sweetify.error(request, 'Error sending follow-up. Please try again.', timer=3000)
            return redirect('my_assistance')
    
    # If GET request, redirect to assistance page
    return redirect('my_assistance')




