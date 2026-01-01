from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from core.models import Admin
import sweetify
from admins.user_activity_utils import log_login_attempt, log_logout


# Staff Login
def staff_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        try:
            staff_member = Admin.objects.get(username=username)
            
            if check_password(password, staff_member.password):
                # Set session variables
                request.session['staff_id'] = staff_member.id
                request.session['staff_username'] = staff_member.username
                request.session['staff_fullname'] = staff_member.get_full_name()
                request.session['role'] = staff_member.role
                request.session['department'] = staff_member.department
                request.session['position'] = staff_member.position
                request.session['first_name'] = staff_member.first_name
                request.session['last_name'] = staff_member.last_name

                # Log successful login
                log_login_attempt(
                    user=staff_member,
                    is_successful=True,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )

                sweetify.success(request, 'Login successful!', icon='success', timer=1500, persistent="Okay")
                return redirect('staff_dashboard')
            else:
                # Log failed login - incorrect password
                log_login_attempt(
                    user=staff_member,
                    is_successful=False,
                    error_message='Incorrect password',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
                sweetify.error(request, 'Invalid username or password.', icon='error', timer=1500, persistent="Okay")
                return redirect('staff_login')
        except Admin.DoesNotExist:
            # Log failed login - user not found
            from admins.user_activity_utils import log_activity
            log_activity(
                user=None,
                activity_type='login_failed',
                activity_category='authentication',
                description=f'Failed login attempt with username: {username}',
                is_successful=False,
                error_message='User not found',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'username': username}
            )
            sweetify.error(request, 'Invalid username or password.', icon='error', timer=1500, persistent="Okay")

    return render(request, 'staff_login.html')


# Staff Logout
def staff_logout(request):
    staff_id = request.session.get('staff_id')
    
    # Log logout before flushing session
    if staff_id:
        try:
            staff_member = Admin.objects.get(id=staff_id)
            log_logout(
                user=staff_member,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        except Admin.DoesNotExist:
            pass
    
    request.session.flush()
    sweetify.success(request, 'Logged out successfully.', icon='success', timer=1500, persistent="Okay")
    return redirect('staff_login')










