def get_current_user(request):
    user_info = {
        'id': request.session.get('id'),
        'first_name': request.session.get('first_name'),
        'middle_name': request.session.get('middle_name'),
        'last_name': request.session.get('last_name'),
        'full_name': request.session.get('full_name'),
        'address': request.session.get('address'),
        'phone': request.session.get('phone'),
        'email': request.session.get('email'),
    }
    return {'user': user_info}


