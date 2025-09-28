def get_current_user(request):
    from core.models import User
    
    user_id = request.session.get('id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            return {'user': user}
        except User.DoesNotExist:
            pass
    
    # Fallback to session data if user not found in database
    user_info = {
        'id': request.session.get('id'),
        'role': request.session.get('role'),
        'first_name': request.session.get('first_name'),
        'middle_name': request.session.get('middle_name'),
        'last_name': request.session.get('last_name'),
        'address': request.session.get('address'),
        'phone': request.session.get('phone'),
        'email': request.session.get('email'),
    }
    return {'user': user_info}


def get_admin_info(request):
    admin_info = {
        'id': request.session.get('admin_id'),
        'username': request.session.get('admin_username'),
        'email': request.session.get('admin_email'),
        'first_name': request.session.get('admin_first_name'),
        'last_name': request.session.get('admin_last_name'),
        'full_name': request.session.get('admin_full_name'),
        'role': request.session.get('admin_role'),
    }
    return {'admin': admin_info}

