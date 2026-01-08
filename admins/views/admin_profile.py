from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from core.models import StaffAdmin
import sweetify
from admins.user_activity_utils import log_activity



def admin_profile(request):
    """View and update admin profile"""
    # Check if admin is logged in
    if not request.session.get('admin_id'):
        sweetify.error(request, 'Please login to access this page.', timer=3000)
        return redirect('admin_login')
    
    admin_id = request.session.get('admin_id')
    admin = StaffAdmin.objects.get(id=admin_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            middle_name = request.POST.get('middle_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            suffix = request.POST.get('suffix', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            email = request.POST.get('email', '').strip()
            username = request.POST.get('username', '').strip()
            department = request.POST.get('department', '').strip()
            position = request.POST.get('position', '').strip()
            
            # Validation
            if not all([first_name, last_name, email, username, department, position]):
                sweetify.error(request, 'Please fill in all required fields.', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
            
            # Check if username is taken by another admin
            if StaffAdmin.objects.filter(username=username).exclude(id=admin_id).exists():
                sweetify.error(request, 'Username already taken.', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
            
            # Check if email is taken by another admin
            if StaffAdmin.objects.filter(email=email).exclude(id=admin_id).exists():
                sweetify.error(request, 'Email already taken.', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
            
            try:
                # Update admin profile
                admin.first_name = first_name
                admin.middle_name = middle_name
                admin.last_name = last_name
                admin.suffix = suffix
                admin.phone_number = phone_number
                admin.email = email
                admin.username = username
                admin.department = department
                admin.position = position
                admin.save()
                
                # Log activity
                log_activity(
                    user=admin,
                    activity_type='profile_updated',
                    activity_category='account_management',
                    description=f'{admin.get_full_name()} updated their profile',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
                
                sweetify.success(request, 'Profile updated successfully!', timer=3000, icon='success', button='OK')
                return redirect('admin_profile')
                
            except Exception as e:
                sweetify.error(request, f'Error updating profile: {str(e)}', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
        
        elif action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            # Validation
            if not all([current_password, new_password, confirm_password]):
                sweetify.error(request, 'Please fill in all password fields.', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
            
            # Verify current password
            if not check_password(current_password, admin.password):
                sweetify.error(request, 'Current password is incorrect.', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
            
            # Check if new passwords match
            if new_password != confirm_password:
                sweetify.error(request, 'New passwords do not match.', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
            
            # Check password length
            if len(new_password) < 8:
                sweetify.error(request, 'Password must be at least 8 characters long.', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
            
            try:
                # Hash and update password
                hashed_password = make_password(new_password)
                admin.password = hashed_password
                admin.save()
                
                # Log activity
                log_activity(
                    user=admin,
                    activity_type='password_changed',
                    activity_category='security',
                    description=f'{admin.get_full_name()} changed their password',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
                
                sweetify.success(request, 'Password changed successfully!', timer=3000)
                return redirect('admin_profile')
                
            except Exception as e:
                sweetify.error(request, f'Error changing password: {str(e)}', timer=3000)
                return render(request, 'admin_profile.html', {'admin': admin})
    
    # GET request - display profile
    context = {
        'admin': admin
    }
    return render(request, 'admin_profile.html', context)