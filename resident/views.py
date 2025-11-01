from core.models import User, Admin
from django.shortcuts import render
from django.contrib.auth import logout
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.shortcuts import redirect, get_object_or_404
from django.db import IntegrityError
from django.http import JsonResponse
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Q
import os, uuid, time


from . import file_upload_view
from .models import ForumPost, PostReaction, PostComment, CommentReaction
from admins.notification_utils import notify_new_case_filed
from admins.models import Complaint, AssistanceRequest, ComplaintAttachment, AssistanceAttachment
from admins.models import Notification
import sweetify



def resident_dashboard(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to access the dashboard.', timer=3000)
        return redirect('homepage')
    user_id = request.session.get('resident_id')
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
        priority = request.POST.get('priority', 'low')
        location_description = request.POST.get('location', '').strip()
        address = request.POST.get('address', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        user_id = request.session.get('resident_id')
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


def my_complaints(request):
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to view your complaints.', persistent=True, timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    complaints = Complaint.objects.filter(user=user).order_by('-created_at')
    return render(request, 'my_complaints.html', {'complaints': complaints})


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
        urgency = request.POST.get('urgency', 'normal')
        
        if not message:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Follow-up message is required.'})
            sweetify.error(request, 'Follow-up message is required.', timer=3000)
            return redirect('my_complaints')
        
        try:
            from admins.models import Notification
            from core.models import Admin
            
            # Use the unified notification system to notify all admins
            notifications = Notification.notify_admins(
                sender=user,
                title=f'Follow-up on Complaint #{complaint.id}: {complaint.title}',
                message=f'Resident {user.get_full_name()} has sent a follow-up message:\n\n{message}\n\nComplaint Details:\n- Title: {complaint.title}\n- Category: {complaint.category}\n- Status: {complaint.status.replace("_", " ").title()}\n- Priority: {complaint.priority.title()}\n- Filed: {complaint.created_at.strftime("%B %d, %Y at %I:%M %p")}',
                notification_type='status_update',
                action_type='commented',
                priority=urgency,
                related_complaint=complaint
            )
            notifications_created = len(notifications)
            
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
        urgency = request.POST.get('urgency', 'low')
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


def update_assistance(request, pk):
    user_id = request.session.get('resident_id')
    if not user_id:
        sweetify.error(request, 'Action not allowed.', persistent="Okay", timer=3000)
        return redirect('homepage')
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
        sweetify.success(request, 'Assistance updated.', persistent="Okay", timer=2000)
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
        urgency = request.POST.get('urgency', 'normal')
        
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
                priority=urgency,
                related_assistance=assistance
            )
            notifications_created = len(notifications)
            
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


# Profile Views
def profile(request):
    """
    Resident profile page: view info, upload profile picture, update password.
    """
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    
    if not user:
        sweetify.error(request, 'You must be logged in to view your profile.', persistent="Okay", timer=3000)
        return redirect('homepage')

    if request.method == 'POST':
        # Handle profile picture upload
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            file_upload_view.handle_profile_picture_upload(request, user, profile_picture)

        firstname = request.POST.get('first_name', '').strip()
        middlename = request.POST.get('middle_name', '').strip()
        lastname = request.POST.get('last_name', '').strip()
        suffix = request.POST.get('suffix', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        address = request.POST.get('address', '').strip()

        # Update user profile information
        user.first_name = firstname
        user.middle_name = middlename
        user.last_name = lastname   
        user.suffix = suffix
        user.email = email
        user.phone_number = phone_number
        user.address = address
        user.save()

        sweetify.success(request, 'Profile updated successfully.', timer=2000)
        
        return redirect('profile')

    context = {
        'user': user,
    }
    return render(request, 'profile.html', context)


def resident_change_password(request):
    user_id = request.session.get('resident_id')
    if not user_id:
        sweetify.error(request, 'You must be logged in to change your password.', persistent="Okay", timer=3000)
        return redirect('homepage')
    
    if request.method == 'POST':
        user = User.objects.filter(id=user_id).first()

        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not (current_password and new_password and confirm_password):
            sweetify.error(request, 'Please fill in all password fields.', timer=3000, persistent=True)
            return redirect('profile')
        
        if not check_password(current_password, user.password):
            sweetify.error(request, 'Current password is incorrect.', timer=3000, persistent=True)
            return redirect('profile')
        
        if new_password != confirm_password:
            sweetify.error(request, 'New passwords do not match.', timer=3000, persistent=True)
            return redirect('profile')
        
        if len(new_password) < 6:
            sweetify.error(request, 'New password must be at least 6 characters.', timer=3000, persistent=True)
            return redirect('profile')
        
        user.password = make_password(new_password)
        user.save()
        sweetify.success(request, 'Password updated successfully.', timer=2000, persistent=True)
        return redirect('profile')



# Community Forum Views
def community_forum(request):
    """Display the community forum with posts and filtering options."""
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to access the community forum.', timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    
    # Get filter parameters
    category = request.GET.get('category', '')
    search = request.GET.get('search', '')
    
    # Base query for active posts
    posts = ForumPost.objects.filter(is_active=True).select_related('author').prefetch_related('reactions', 'comments')
    
    # Apply filters
    if category:
        posts = posts.filter(category=category)
    
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search) |
            Q(author__first_name__icontains=search) |
            Q(author__last_name__icontains=search)
        )
    
    # Paginate posts
    paginator = Paginator(posts, 10)  # 10 posts per page
    page_number = request.GET.get('page')
    posts_page = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = ForumPost.CATEGORY_CHOICES
    
    # Get stats for sidebar
    total_posts = ForumPost.objects.filter(is_active=True).count()
    my_posts = ForumPost.objects.filter(author=user, is_active=True).count()
    
    context = {
        'posts': posts_page,
        'categories': categories,
        'current_category': category,
        'search_query': search,
        'total_posts': total_posts,
        'my_posts': my_posts,
        'current_user': user,
    }
    
    return render(request, 'community_forum.html', context)


def create_post(request):
    """Create a new forum post."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    if request.method == 'POST':
        user_id = request.session.get('resident_id')
        user = User.objects.filter(id=user_id).first()
        
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', 'discussions')
        image = request.FILES.get('image')
        
        if not all([title, content]):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Title and content are required.'})
            sweetify.error(request, 'Title and content are required.', timer=3000)
            return redirect('community_forum')
        
        try:
            post = ForumPost.objects.create(
                author=user,
                title=title,
                content=content,
                category=category,
                image=image if image else None
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Post created successfully!'})
            
            sweetify.success(request, 'Post created successfully!', timer=3000)
            return redirect('community_forum')
            
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Error creating post. Please try again.'})
            
            sweetify.error(request, 'Error creating post. Please try again.', timer=3000)
            return redirect('community_forum')
    
    return redirect('community_forum')


def toggle_reaction(request, post_id):
    """Toggle reaction on a post (like, love, support)."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    if request.method == 'POST':
        user_id = request.session.get('resident_id')
        user = User.objects.filter(id=user_id).first()
        post = get_object_or_404(ForumPost, id=post_id, is_active=True)
        reaction_type = request.POST.get('reaction_type', 'like')
        
        try:
            # Check if user already reacted to this post
            existing_reaction = PostReaction.objects.filter(user=user, post=post).first()
            
            if existing_reaction:
                if existing_reaction.reaction_type == reaction_type:
                    # Same reaction - remove it
                    existing_reaction.delete()
                    action = 'removed'
                else:
                    # Different reaction - update it
                    existing_reaction.reaction_type = reaction_type
                    existing_reaction.save()
                    action = 'updated'
            else:
                # No existing reaction - create new one
                PostReaction.objects.create(user=user, post=post, reaction_type=reaction_type)
                action = 'added'
            
            # Get updated counts
            like_count = post.get_like_count()
            love_count = post.get_love_count()
            support_count = post.get_support_count()
            total_reactions = post.get_total_reactions()
            
            return JsonResponse({
                'success': True,
                'action': action,
                'like_count': like_count,
                'love_count': love_count,
                'support_count': support_count,
                'total_reactions': total_reactions,
                'user_reaction': existing_reaction.reaction_type if existing_reaction and action != 'removed' else None
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Error processing reaction.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def add_comment(request, post_id):
    """Add a comment to a post."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    if request.method == 'POST':
        user_id = request.session.get('resident_id')
        user = User.objects.filter(id=user_id).first()
        post = get_object_or_404(ForumPost, id=post_id, is_active=True)
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'message': 'Comment content is required.'})
        
        try:
            comment = PostComment.objects.create(
                post=post,
                author=user,
                content=content
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Comment added successfully!',
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'author_name': comment.author.get_full_name(),
                    'author_initials': comment.author.first_name[0].upper() + (comment.author.last_name[0].upper() if comment.author.last_name else ''),
                    'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
                },
                'total_comments': post.get_total_comments()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Error adding comment.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def delete_post(request, post_id):
    """Delete a forum post (only by author)."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    post = get_object_or_404(ForumPost, id=post_id, author=user)
    
    try:
        post.is_active = False
        post.save()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Post deleted successfully!'})
        
        sweetify.success(request, 'Post deleted successfully!', timer=3000)
        return redirect('community_forum')
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Error deleting post.'})
        
        sweetify.error(request, 'Error deleting post.', timer=3000)
        return redirect('community_forum')


def edit_post(request, post_id):
    """Edit a forum post (only by author)."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    post = get_object_or_404(ForumPost, id=post_id, author=user, is_active=True)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', post.category)
        
        if not all([title, content]):
            return JsonResponse({'success': False, 'message': 'Title and content are required.'})
        
        try:
            post.title = title
            post.content = content
            post.category = category
            
            # Handle image update
            if request.FILES.get('image'):
                post.image = request.FILES['image']
            
            post.save()
            
            return JsonResponse({'success': True, 'message': 'Post updated successfully!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Error updating post.'})
    
    # Return post data for editing
    return JsonResponse({
        'success': True,
        'post': {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'category': post.category,
        }
    })


def get_post_comments(request, post_id):
    """Get comments for a specific post."""
    post = get_object_or_404(ForumPost, id=post_id, is_active=True)
    comments = post.comments.filter(is_active=True).select_related('author').order_by('created_at')
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'author_name': comment.author.get_full_name(),
            'author_initials': comment.author.first_name[0].upper() + (comment.author.last_name[0].upper() if comment.author.last_name else ''),
            'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
            'can_delete': request.session.get('resident_id') == comment.author.id,
        })
    
    return JsonResponse({
        'success': True,
        'comments': comments_data,
        'total_comments': len(comments_data)
    })


def delete_comment(request, comment_id):
    """Delete a comment (only by author)."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    comment = get_object_or_404(PostComment, id=comment_id, author=user)
    
    try:
        comment.is_active = False
        comment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Comment deleted successfully!',
            'total_comments': comment.post.get_total_comments()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error deleting comment.'})


# Notifications View
def notifications(request):
    """Display resident notifications."""
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to view notifications.', timer=3000)
        return redirect('homepage')
 
    notif_type = request.GET.get('type', '')
    notif_status = request.GET.get('status', '')
    page_number = request.GET.get('page', 1)


    user_content_type = ContentType.objects.get_for_model(user)

    notifications  = Notification.objects.filter(
        recipient_content_type=user_content_type,
        recipient_object_id=user.id,
    ).order_by('-created_at')

    if notif_status == '':
        notifications = notifications.filter(is_archived=False)

    # Apply filters
    if notif_type:
        notifications = notifications.filter(notification_type__icontains=notif_type)

    if notif_status:
        if notif_status == 'unread':
            notifications = notifications.filter(is_read=False)
        elif notif_status == 'read':
            notifications = notifications.filter(is_read=True)
        elif notif_status == 'archived':
            notifications = notifications.filter(is_archived=True)

    paginator = Paginator(notifications, 5)  # 5 notifications per page
    page_object = paginator.get_page(page_number)

    notification_types = [types[0] for types in Notification.NOTIFICATION_TYPES]

    context = {
        'notifications': page_object,
        'notification_types': notification_types,
        'current_type': notif_type,
        'current_status': notif_status,
        'page_obj': page_object,
    }

    return render(request, 'resident_notifications.html', context)


def resident_notification_details(request, notification_id):
    """Display details of a specific notification."""
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to view notifications.', timer=3000)
        return redirect('homepage')

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient_content_type=ContentType.objects.get_for_model(user),
        recipient_object_id=user.id
    )

    # Mark as read
    if not notification.is_read:
        notification.is_read = True
        notification.save()

    context = {
        'notification': notification,
    }

    return render(request, 'resident_notification_details.html', context)


def resident_mark_notification_read(request, notification_id):
    """Mark a notification as read."""
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to manage notifications.', timer=3000)
        return redirect('homepage')

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient_content_type=ContentType.objects.get_for_model(user),
        recipient_object_id=user.id
    )

    notification.is_read = True
    notification.save()
    sweetify.success(request, 'Notification marked as read.', timer=2000, persistent=True)
    return redirect('notifications')

def resident_archive_notification(request, notification_id):
    """Archive a notification."""
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()

    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to manage notifications.', timer=3000, persistent=True)
        return redirect('homepage')

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient_content_type=ContentType.objects.get_for_model(user),
        recipient_object_id=user.id
    )

    notification.is_archived = True
    notification.save()
    sweetify.success(request, 'Notification archived.', timer=2000, persistent=True)
    return redirect('notifications')

# Logout View
def resident_logout(request):
    logout(request)
    sweetify.toast(request, 'You have been logged out successfully.', timer=3000)
    return redirect('homepage')
