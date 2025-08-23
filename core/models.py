from django.db import models

# Create your models here.

class User(models.Model):
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=100, default='')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    password = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='uploads/profile_pictures/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class StaffAdmin(models.Model):
    # Account Information
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, default='staff', choices=[
        ('admin', 'Admin'),
        ('staff', 'Staff')
    ])
    department = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=20, blank=True, null=True)
    
    # Legacy field for backward compatibility
    full_name = models.CharField(max_length=250, blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_admin'  # Keep the same table name for backward compatibility
        verbose_name = 'Staff/Admin Account'
        verbose_name_plural = 'Staff/Admin Accounts'

    def save(self, *args, **kwargs):
        # Auto-generate full_name from individual name components
        name_parts = [self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        name_parts.append(self.last_name)
        if self.suffix:
            name_parts.append(self.suffix)
        self.full_name = ' '.join(name_parts)
        super().save(*args, **kwargs)

    def get_full_name(self):
        """Return the formatted full name"""
        name_parts = [self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        name_parts.append(self.last_name)
        if self.suffix:
            name_parts.append(self.suffix)
        return ' '.join(name_parts)

    def get_short_name(self):
        """Return first name and last name only"""
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"


# Backward compatibility alias
Admin = StaffAdmin