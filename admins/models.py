from django.db import models
from django.utils import timezone
from core.models import User, Admin


# Create your models here.
class Complaint(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50)
    priority = models.CharField(max_length=20, default='low')
    status = models.CharField(max_length=20, default='pending')
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

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    type = models.CharField(max_length=50)
    urgency = models.CharField(max_length=20, default='low')
    status = models.CharField(max_length=20, default='pending')
    address = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    assigned_to = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL)
    admin_remarks = models.TextField(blank=True, null=True)
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


# Admin Notifications Table
class Admin_Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('case_assignment', 'Case Assignment'),
        ('status_update', 'Status Update'), 
        ('new_complaint', 'New Complaint'),
        ('new_assistance', 'New Assistance Request'),
        ('case_resolved', 'Case Resolved'),
        ('case_closed', 'Case Closed'),
        ('urgent_case', 'Urgent Case'),
        ('system_alert', 'System Alert'),
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
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    recipient = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='received_notifications')
    sender = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='other')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default='created')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    
    # Related case information
    related_complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    related_assistance = models.ForeignKey(AssistanceRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    # Notification state
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        db_table = 'admin_notifications'
        verbose_name = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} - {self.title} (To: {self.recipient.username})"
    
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


class Resident_Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('status_update', 'Status Update'),
        ('case_assigned', 'Case Assigned'),
        ('case_resolved', 'Case Resolved'),
        ('case_closed', 'Case Closed'),
        ('request_approved', 'Request Approved'),
        ('request_rejected', 'Request Rejected'),
        ('admin_response', 'Admin Response'),
        ('system_alert', 'System Alert'),
        ('announcement', 'Announcement'),
        ('reminder', 'Reminder'),
        ('other', 'Other'),
    ]
    
    ACTION_TYPES = [
        ('status_changed', 'Status Changed'),
        ('assigned', 'Assigned'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('commented', 'Commented'),
        ('updated', 'Updated'),
        ('created', 'Created'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications')
    sender = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_resident_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='other')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default='created')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    
    # Related case information
    related_complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, null=True, blank=True, related_name='resident_notifications')
    related_assistance = models.ForeignKey(AssistanceRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='resident_notifications')
    
    # Notification state
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'resident_notifications'
        verbose_name = 'Resident Notification'
        verbose_name_plural = 'Resident Notifications'
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} - {self.title} (To: {self.recipient.email})"
    
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