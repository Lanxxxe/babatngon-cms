from django.db import models

# Create your models here.

class User(models.Model):
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=100, default='')
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100, unique=True, blank=True, null=True, default=None)
    phone = models.CharField(max_length=20, blank=True, null=True)
    barangay = models.CharField(max_length=100, blank=True, null=True, default=None)
    address = models.TextField(blank=True, null=True)
    password = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='uploads/profile_pictures/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

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
        db_table = 'staff_admin' 
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


class Feedback(models.Model):
    """User feedback about the system"""
    RATING_CHOICES = [
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]
    
    CATEGORY_CHOICES = [
        ('general', 'General Feedback'),
        ('complaint', 'Complaint System'),
        ('assistance', 'Assistance Request'),
        ('interface', 'User Interface'),
        ('performance', 'System Performance'),
        ('suggestion', 'Suggestion'),
        ('bug', 'Bug Report'),
        ('other', 'Other'),
    ]
    
    # User Information
    name = models.CharField(max_length=200, help_text="Your full name")
    email = models.EmailField(help_text="Your email address")
    
    # Feedback Details
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    rating = models.IntegerField(choices=RATING_CHOICES, help_text="Rate your overall experience")
    subject = models.CharField(max_length=200, help_text="Brief subject of your feedback")
    message = models.TextField(help_text="Detailed feedback message")
    
    # Optional user reference (if logged in)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    
    # Metadata
    is_read = models.BooleanField(default=False)
    is_responded = models.BooleanField(default=False)
    admin_response = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'feedback'
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedbacks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject} ({self.get_rating_display()})"
    
    def get_rating_stars(self):
        """Return a string of star emojis based on rating"""
        return '⭐' * self.rating








