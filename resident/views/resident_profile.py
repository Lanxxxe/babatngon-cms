from core.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password, make_password
from resident.file_upload_view import handle_profile_picture_upload
import sweetify



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
            handle_profile_picture_upload(request, user, profile_picture)

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

