from django.conf import settings
import os

# Utility function for handling profile picture upload
def handle_profile_picture_upload(request, user, uploaded_file):
    """
    Handles saving the uploaded profile picture for the user.
    Deletes the old picture if it exists.
    """
    if not uploaded_file:
        return
    # Save to uploads/profile_pictures/<user_id>_<filename>
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'profile_pictures')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{user.id}_{uploaded_file.name}"
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    # Remove old picture if exists and is not default
    if user.profile_picture and os.path.exists(user.profile_picture.path):
        try:
            os.remove(user.profile_picture.path)
        except Exception:
            pass
    # Update user profile_picture field
    user.profile_picture = f"profile_pictures/{filename}"
    user.save()

