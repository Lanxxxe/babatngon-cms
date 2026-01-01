from core.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password, make_password
from resident.file_upload_view import handle_profile_picture_upload
import sweetify
from admins.user_activity_utils import log_activity



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
        # Track what was updated
        updates = []
        
        # Handle profile picture upload
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            handle_profile_picture_upload(request, user, profile_picture)
            updates.append('profile picture')

        firstname = request.POST.get('first_name', '').strip()
        middlename = request.POST.get('middle_name', '').strip()
        lastname = request.POST.get('last_name', '').strip()
        suffix = request.POST.get('suffix', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        address = request.POST.get('address', '').strip()

        # Track changes
        if firstname != user.first_name:
            updates.append('first name')
        if middlename != user.middle_name:
            updates.append('middle name')
        if lastname != user.last_name:
            updates.append('last name')
        if suffix != user.suffix:
            updates.append('suffix')
        if email != user.email:
            updates.append('email')
        if phone_number != user.phone:
            updates.append('phone')
        if address != user.address:
            updates.append('address')

        # Update user profile information
        user.first_name = firstname
        user.middle_name = middlename
        user.last_name = lastname   
        user.suffix = suffix
        user.email = email
        user.phone = phone_number
        user.address = address
        user.save()

        # Log activity
        if updates:
            updated_fields = ', '.join(updates)
            log_activity(
                user=user,
                activity_type='user_updated',
                activity_category='administration',
                description=f'{user.get_full_name()} updated profile: {updated_fields}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'updated_fields': updates}
            )

        sweetify.success(request, 'Profile updated successfully.', timer=2000)
        
        return redirect('profile')
    
    # Log profile view (for GET requests)
    log_activity(
        user=user,
        activity_type='user_viewed',
        activity_category='administration',
        description=f'{user.get_full_name()} viewed their profile',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )

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
            # Log failed attempt
            log_activity(
                user=user,
                activity_type='password_change',
                activity_category='authentication',
                description=f'{user.get_full_name()} failed to change password: missing fields',
                is_successful=False,
                error_message='Missing required password fields',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            sweetify.error(request, 'Please fill in all password fields.', timer=3000, persistent=True)
            return redirect('profile')
        
        if not check_password(current_password, user.password):
            # Log failed attempt
            log_activity(
                user=user,
                activity_type='password_change',
                activity_category='authentication',
                description=f'{user.get_full_name()} failed to change password: incorrect current password',
                is_successful=False,
                error_message='Current password is incorrect',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            sweetify.error(request, 'Current password is incorrect.', timer=3000, persistent=True)
            return redirect('profile')
        
        if new_password != confirm_password:
            # Log failed attempt
            log_activity(
                user=user,
                activity_type='password_change',
                activity_category='authentication',
                description=f'{user.get_full_name()} failed to change password: passwords do not match',
                is_successful=False,
                error_message='New passwords do not match',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            sweetify.error(request, 'New passwords do not match.', timer=3000, persistent=True)
            return redirect('profile')
        
        if len(new_password) < 6:
            # Log failed attempt
            log_activity(
                user=user,
                activity_type='password_change',
                activity_category='authentication',
                description=f'{user.get_full_name()} failed to change password: password too short',
                is_successful=False,
                error_message='Password must be at least 6 characters',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            sweetify.error(request, 'New password must be at least 6 characters.', timer=3000, persistent=True)
            return redirect('profile')
        
        user.password = make_password(new_password)
        user.save()
        
        # Log successful password change
        log_activity(
            user=user,
            activity_type='password_change',
            activity_category='authentication',
            description=f'{user.get_full_name()} successfully changed password',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        sweetify.success(request, 'Password updated successfully.', timer=2000, persistent=True)
        return redirect('profile')

