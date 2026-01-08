from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from core.models import Admin
import sweetify
from admins.user_activity_utils import log_activity

# Accounts management view
def accounts(request):
    """
    List all staff and admin accounts for management.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    admins = Admin.objects.all().order_by('-role', 'username')
    admin_count = Admin.objects.filter(role='admin').count()
    
    # Log activity
    admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
    if admin_user:
        log_activity(
            user=admin_user,
            activity_type='user_viewed',
            activity_category='administration',
            description=f'{admin_user.get_full_name()} accessed accounts management page',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
    
    context = {
        'admins': admins,
        'admin_count': admin_count,
    }
    return render(request, 'accounts.html', context)


# Register new staff/admin
@require_POST
def add_account(request):
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    
    try:

        
        # Account Information
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        role = request.POST.get('role', 'staff').strip()
        department = request.POST.get('department', '').strip()
        position = request.POST.get('position', '').strip()
        
        # Personal Information
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        suffix = request.POST.get('suffix', '').strip()
        
        # Security
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        # Validation
        required_fields = [username, email, role, department, position, first_name, last_name, password]
        if not all(required_fields):
            sweetify.error(request, 'Please fill in all required fields.', timer=3000)
            return redirect('accounts')
        
        # Password validation
        if password != confirm_password:
            sweetify.error(request, 'Passwords do not match.', timer=3000)
            return redirect('accounts')
        
        if len(password) < 8:
            sweetify.error(request, 'Password must be at least 8 characters long.', timer=3000)
            return redirect('accounts')
        
        # Check for existing username
        if Admin.objects.filter(username=username).exists():
            sweetify.error(request, 'Username already exists.', timer=3000)
            return redirect('accounts')
        
        # Check for existing email
        if Admin.objects.filter(email=email).exists():
            sweetify.error(request, 'Email already exists.', timer=3000)
            return redirect('accounts')
        
        # Create the account
        new_admin = Admin.objects.create(
            username=username,
            email=email,
            phone_number=phone_number,
            role=role,
            department=department,
            position=position,
            first_name=first_name,
            middle_name=middle_name if middle_name else None,
            last_name=last_name,
            suffix=suffix if suffix else None,
            password=make_password(password)
        )
        
        full_name = f"{first_name} {last_name}"
        
        # Log activity
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_created',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} created new {role} account for {full_name} ({username})',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'new_user_id': new_admin.id, 'new_user_role': role, 'new_user_username': username}
            )
        
        sweetify.toast(request, f'Account for {full_name} registered successfully!', timer=2000)
        
    except Exception as e:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_created',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} failed to create new account',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'Failed to register account. Please try again.', timer=3000)
    
    return redirect('accounts')

# Change password for staff/admin
@require_POST
def change_account_password(request):
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    try:
        admin_id = request.POST.get('admin_id')
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        admin = Admin.objects.filter(id=admin_id).first()
        if not admin:
            sweetify.error(request, 'Account not found.', timer=3000)
            return redirect('accounts')
        if not new_password or new_password != confirm_password:
            sweetify.error(request, 'Passwords do not match.', timer=3000)
            return redirect('accounts')
        if len(new_password) < 6:
            sweetify.error(request, 'Password must be at least 6 characters.', timer=3000)
            return redirect('accounts')
        admin.password = make_password(new_password)
        admin.save()
        
        # Log activity
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='password_change',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} changed password for account {admin.get_full_name()} ({admin.username})',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'target_user_id': admin.id, 'target_username': admin.username}
            )
        
        sweetify.toast(request, 'Password updated successfully.', timer=2000)
    except Exception as e:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='password_change',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} failed to change password for account',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'Failed to update password.', timer=3000)
    return redirect('accounts')

# Delete staff/admin account
@require_POST
def delete_account(request):
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')
    try:
        admin_id = request.POST.get('admin_id')
        admin = Admin.objects.filter(id=admin_id).first()
        if not admin:
            sweetify.error(request, 'Account not found.', timer=3000)
            return redirect('accounts')
        if admin.role == 'admin':
            admin_count = Admin.objects.filter(role='admin').count()
            if admin_count <= 1:
                sweetify.error(request, 'Cannot delete the only remaining admin.', timer=3000)
                return redirect('accounts')
        
        # Store info before deletion
        deleted_name = admin.get_full_name()
        deleted_username = admin.username
        deleted_role = admin.role
        
        admin.delete()
        
        # Log activity
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_deleted',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} deleted {deleted_role} account {deleted_name} ({deleted_username})',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'deleted_username': deleted_username, 'deleted_role': deleted_role}
            )
        
        sweetify.toast(request, 'Account deleted successfully.', timer=2000)
    except Exception as e:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_deleted',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} failed to delete account',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'Failed to delete account.', timer=3000)
    return redirect('accounts')


