from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from core.models import Admin
import sweetify


# Staff Profile Management
def staff_profile(request):
    """
    Display staff profile information.
    """
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        context = {
            'current_staff': current_staff,
        }
        
        return render(request, 'staff_profile.html', context)
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    except Exception as e:
        sweetify.error(request, f'Error loading profile: {str(e)}')
        return redirect('staff_dashboard')


def staff_update_profile(request):
    """
    Update staff profile information.
    """
    if request.method != 'POST':
        return redirect('staff_profile')
    
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        suffix = request.POST.get('suffix', '').strip()
        email = request.POST.get('email', '').strip()
        department = request.POST.get('department', '').strip()
        position = request.POST.get('position', '').strip()
        
        # Validate required fields
        if not all([first_name, last_name, email, department, position]):
            sweetify.error(request, 'Please fill in all required fields.')
            return redirect('staff_profile')
        
        # Check if email is already taken by another admin
        if Admin.objects.filter(email=email).exclude(id=current_staff.id).exists():
            sweetify.error(request, 'Email address is invalid.')
            return redirect('staff_profile')
        
        # Update staff profile
        current_staff.first_name = first_name
        current_staff.middle_name = middle_name if middle_name else None
        current_staff.last_name = last_name
        current_staff.suffix = suffix if suffix else None
        current_staff.email = email
        current_staff.department = department
        current_staff.position = position
        
        current_staff.save()
        
        sweetify.success(request, 'Profile updated successfully.')
        return redirect('staff_profile')
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    except Exception as e:
        sweetify.error(request, f'Error updating profile: {str(e)}')
        return redirect('staff_profile')


def staff_change_password(request):
    """
    Change staff password.
    """
    if request.method != 'POST':
        return redirect('staff_profile')
    
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get form data
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validate inputs
        if not all([current_password, new_password, confirm_password]):
            sweetify.error(request, 'Please fill in all password fields.')
            return redirect('staff_profile')
        
        # Check current password
        if not check_password(current_password, current_staff.password):
            sweetify.error(request, 'Current password is incorrect.')
            return redirect('staff_profile')
        
        # Check if new passwords match
        if new_password != confirm_password:
            sweetify.error(request, 'New passwords do not match.')
            return redirect('staff_profile')
        
        # Validate new password strength
        if len(new_password) < 8:
            sweetify.error(request, 'New password must be at least 8 characters long.')
            return redirect('staff_profile')
        
        # Update password
        current_staff.password = make_password(new_password)
        current_staff.save()
        
        sweetify.success(request, 'Password changed successfully.')
        return redirect('staff_profile')
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    except Exception as e:
        sweetify.error(request, f'Error changing password: {str(e)}')
        return redirect('staff_profile')


def staff_update_username(request):
    """
    Update staff username.
    """
    if request.method != 'POST':
        return redirect('staff_profile')
    
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get form data
        new_username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Validate inputs
        if not all([new_username, password]):
            sweetify.error(request, 'Please provide both username and password.')
            return redirect('staff_profile')
        
        # Check current password
        if not check_password(password, current_staff.password):
            sweetify.error(request, 'Password is incorrect.')
            return redirect('staff_profile')
        
        # Check if username is already taken
        if Admin.objects.filter(username=new_username).exclude(id=current_staff.id).exists():
            sweetify.error(request, 'Username is already taken.')
            return redirect('staff_profile')
        
        # Validate username format
        if len(new_username) < 3:
            sweetify.error(request, 'Username must be at least 3 characters long.')
            return redirect('staff_profile')
        
        if not new_username.isalnum():
            sweetify.error(request, 'Username can only contain letters and numbers.')
            return redirect('staff_profile')
        
        # Update username
        current_staff.username = new_username
        current_staff.save()
        
        sweetify.success(request, 'Username updated successfully.')
        return redirect('staff_profile')
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    except Exception as e:
        sweetify.error(request, f'Error updating username: {str(e)}')
        return redirect('staff_profile')













