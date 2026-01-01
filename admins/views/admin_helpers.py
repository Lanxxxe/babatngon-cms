from django.shortcuts import redirect, render
from django.contrib.auth.hashers import check_password, make_password
import sweetify

from core.models import Admin
from admins.user_activity_utils import log_login_attempt, log_logout


def admin_login(request):

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        try:
            admin = Admin.objects.filter(username=username).first()
            if not admin:
                # Create a temporary admin object for logging failed attempt
                temp_admin = type('obj', (object,), {
                    'id': None,
                    'username': username,
                    'email': '',
                    'role': 'unknown',
                    'get_full_name': lambda: username
                })
                log_login_attempt(
                    user=temp_admin,
                    is_successful=False,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT'),
                    error_message=f'Username not found: {username}'
                )
                sweetify.toast(request, 'Invalid username or password.', timer=3000, icon='error')
                return redirect('admin_login')
            if not check_password(password, admin.password):
                # Log failed login attempt
                log_login_attempt(
                    user=admin,
                    is_successful=False,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT'),
                    error_message='Incorrect password'
                )
                sweetify.toast(request, 'Invalid username or password.', timer=3000, icon='error')
                return redirect('admin_login')
            
            # Set session for admin
            request.session['admin_id'] = admin.id
            request.session['admin_username'] = admin.username
            request.session['admin_email'] = admin.email
            request.session['admin_first_name'] = admin.first_name
            request.session['admin_last_name'] = admin.last_name
            request.session['admin_full_name'] = admin.full_name
            request.session['admin_role'] = admin.role
            
            # Log successful login
            log_login_attempt(
                user=admin,
                is_successful=True,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            sweetify.toast(request, f'Welcome, {admin.full_name}!', timer=2000)

            if admin.role == 'staff':
                return redirect('staff_dashboard')

            elif admin.role == 'admin':
                return redirect('admin_dashboard')

            # return redirect('admin_dashboard')
        except Exception as e:
            # Log exception during login
            if username:
                try:
                    admin = Admin.objects.filter(username=username).first()
                    if admin:
                        log_login_attempt(
                            user=admin,
                            is_successful=False,
                            ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT'),
                            error_message=f'Exception during login: {str(e)}'
                        )
                except:
                    pass  # If we can't log, just continue
            
            sweetify.toast(request, 'An error occurred during login. Please try again.', timer=3000, icon='error')
            return redirect('admin_login')
    return render(request, 'admin_login.html')


def admin_logout(request):
    """
    Admin logout view.
    """
    # Get admin info before clearing session
    admin_id = request.session.get('admin_id')
    
    # Log logout
    if admin_id:
        try:
            admin = Admin.objects.filter(id=admin_id).first()
            if admin:
                log_logout(
                    user=admin,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
        except Exception:
            pass  # If logging fails, continue with logout
    
    request.session.flush()  # Clear all session data
    sweetify.toast(request, 'You have been logged out successfully.', timer=2000)
    return redirect('admin_login')
