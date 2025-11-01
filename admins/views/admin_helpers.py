from django.shortcuts import redirect, render
from django.contrib.auth.hashers import check_password
import sweetify

from core.models import Admin

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        try:
            admin = Admin.objects.filter(username=username).first()
            if not admin:
                sweetify.toast(request, 'Invalid username or password.', timer=3000, icon='error')
                return redirect('admin_login')
            if not check_password(password, admin.password):
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
            sweetify.toast(request, f'Welcome, {admin.full_name}!', timer=2000)

            if admin.role == 'staff':
                return redirect('staff_dashboard')

            elif admin.role == 'admin':
                return redirect('admin_dashboard')

            # return redirect('admin_dashboard')
        except Exception as e:
            sweetify.toast(request, 'An error occurred during login. Please try again.', timer=3000, icon='error')
            return redirect('admin_login')
    return render(request, 'admin_login.html')


def admin_logout(request):
    """
    Admin logout view.
    """
    request.session.flush()  # Clear all session data
    sweetify.toast(request, 'You have been logged out successfully.', timer=2000)
    return redirect('admin_login')
