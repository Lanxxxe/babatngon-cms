from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from core.models import User, Admin


# Create your models here.
class Complaint(models.Model):
    COMPLAINT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('assigned', 'Assigned'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]


    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50)
    priority = models.CharField(max_length=20, default='low', choices=PRIORITY_LEVELS)
    status = models.CharField(max_length=20, default='pending', choices=COMPLAINT_STATUS_CHOICES)
    location_description = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    assigned_to = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL)
    assigned_by = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_complaints')
    admin_remarks = models.TextField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'complaints'
        verbose_name = 'Complaint'
        verbose_name_plural = 'Complaints'


# Assistance Requests Table
class AssistanceRequest(models.Model):
    ASSISTANCE_URGENCY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]    

    ASSISTANCE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('assigned', 'Assigned'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    

    user = models.ForeignKey(User, on_delete=models.CASCADE)    
    title = models.CharField(max_length=200)
    description = models.TextField()
    type = models.CharField(max_length=50)
    urgency = models.CharField(max_length=20, default='low', choices=ASSISTANCE_URGENCY_LEVELS)
    status = models.CharField(max_length=20, default='pending', choices=ASSISTANCE_STATUS_CHOICES)
    address = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    assigned_to = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL)
    assigned_by = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_assistances')
    assigned_date = models.DateTimeField(null=True, blank=True)
    admin_remarks = models.TextField(blank=True, null=True)

    completed_by = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL, related_name='completed_assistances')
    completion_notes = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assistance_requests'
        verbose_name = 'Assistance Request'
        verbose_name_plural = 'Assistance Requests'


# Complaint Attachments Table
class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='complaint_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'complaint_attachments'
        verbose_name = 'Complaint Attachment'
        verbose_name_plural = 'Complaint Attachments'

# Assistance Attachments Table
class AssistanceAttachment(models.Model):
    assistance = models.ForeignKey(AssistanceRequest, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='assistance_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assistance_attachments'
        verbose_name = 'Assistance Attachment'
        verbose_name_plural = 'Assistance Attachments'


# Unified Notification System
class Notification(models.Model):
    """
    Unified notification model that handles all types of notifications:
    - Resident to Admin
    - Resident to Staff  
    - Admin to Staff
    - Staff to Admin
    - Admin to Resident
    - Staff to Resident
    """
    
    NOTIFICATION_TYPES = [
        # Case Management
        ('case_assignment', 'Case Assignment'),
        ('status_update', 'Status Update'), 
        ('new_complaint', 'New Complaint'),
        ('new_assistance', 'New Assistance Request'),
        ('case_resolved', 'Case Resolved'),
        ('case_closed', 'Case Closed'),
        ('urgent_case', 'Urgent Case'),
        
        # Administrative
        ('case_assigned', 'Case Assigned'),
        ('request_approved', 'Request Approved'),
        ('request_rejected', 'Request Rejected'),
        ('admin_response', 'Admin Response'),
        
        # System
        ('system_alert', 'System Alert'),
        ('announcement', 'Announcement'),
        ('reminder', 'Reminder'),
        ('other', 'Other'),
    ]
    
    ACTION_TYPES = [
        ('assigned', 'Assigned'),
        ('status_changed', 'Status Changed'),
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('reassigned', 'Reassigned'),
        ('commented', 'Commented'),
        ('escalated', 'Escalated'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Generic recipient - can be Admin, User (Resident), or Staff
    recipient_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name='notification_recipients'
    )
    recipient_object_id = models.PositiveIntegerField()
    recipient = GenericForeignKey('recipient_content_type', 'recipient_object_id')
    
    # Generic sender - can be Admin, User (Resident), or Staff
    sender_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='notification_senders'
    )
    sender_object_id = models.PositiveIntegerField(null=True, blank=True)
    sender = GenericForeignKey('sender_content_type', 'sender_object_id')
    
    # Notification content
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='other')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default='created')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    
    # Related case information
    related_complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications'
    )
    related_assistance = models.ForeignKey(
        AssistanceRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications'
    )
    
    # Notification state
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_content_type', 'recipient_object_id', 'is_read']),
            models.Index(fields=['sender_content_type', 'sender_object_id']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        recipient_name = getattr(self.recipient, 'get_full_name', lambda: getattr(self.recipient, 'username', str(self.recipient)))()
        return f"{self.notification_type} - {self.title} (To: {recipient_name})"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
    
    def archive(self):
        """Archive the notification"""
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            self.save(update_fields=['is_archived', 'archived_at'])
    
    def get_related_case(self):
        """Get the related case (complaint or assistance request)"""
        if self.related_complaint:
            return self.related_complaint
        elif self.related_assistance:
            return self.related_assistance
        return None
    
    def get_case_type(self):
        """Get the type of related case"""
        if self.related_complaint:
            return 'complaint'
        elif self.related_assistance:
            return 'assistance'
        return None
    
    def get_recipient_type(self):
        """Get the type of recipient (admin, user, staff)"""
        model_name = self.recipient_content_type.model.lower()
        if 'admin' in model_name:
            return 'admin'
        elif 'user' in model_name:
            return 'resident'
        elif 'staff' in model_name:
            return 'staff'
        return 'unknown'
    
    def get_sender_type(self):
        """Get the type of sender (admin, user, staff)"""
        if not self.sender:
            return None
        model_name = self.sender_content_type.model.lower()
        if 'admin' in model_name:
            return 'admin'
        elif 'user' in model_name:
            return 'resident'
        elif 'staff' in model_name:
            return 'staff'
        return 'unknown'
    
    @classmethod
    def create_notification(cls, recipient, sender=None, title='', message='', 
                          notification_type='other', action_type='created', 
                          priority='normal', related_complaint=None, related_assistance=None):
        """
        Helper method to create notifications easily
        
        Usage:
        # Resident to Admin
        Notification.create_notification(
            recipient=admin_user,
            sender=resident_user,
            title="New complaint filed",
            message="A new complaint has been filed...",
            notification_type='new_complaint'
        )
        
        # Admin to Resident  
        Notification.create_notification(
            recipient=resident_user,
            sender=admin_user,
            title="Complaint status updated",
            message="Your complaint has been updated...",
            notification_type='status_update'
        )
        """

        # Get content types
        recipient_ct = ContentType.objects.get_for_model(recipient)
        sender_ct = ContentType.objects.get_for_model(sender) if sender else None
        
        return cls.objects.create(
            recipient_content_type=recipient_ct,
            recipient_object_id=recipient.id,
            sender_content_type=sender_ct,
            sender_object_id=sender.id if sender else None,
            title=title,
            message=message,
            notification_type=notification_type,
            action_type=action_type,
            priority=priority,
            related_complaint=related_complaint,
            related_assistance=related_assistance
        )
    
    @classmethod
    def notify_admins(cls, sender=None, title='', message='', notification_type='other', 
                     action_type='created', priority='normal', related_complaint=None, 
                     related_assistance=None):
        """
        Helper method to notify all active admins
        """
        
        active_admins = Admin.objects.filter(is_active=True)
        notifications = []
        
        for admin in active_admins:
            notification = cls.create_notification(
                recipient=admin,
                sender=sender,
                title=title,
                message=message,
                notification_type=notification_type,
                action_type=action_type,
                priority=priority,
                related_complaint=related_complaint,
                related_assistance=related_assistance
            )
            notifications.append(notification)
        
        return notifications



    

