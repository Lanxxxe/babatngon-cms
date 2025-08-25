from django.db import models
from core.models import User, Admin


# Create your models here.
class Complaint(models.Model):
    # CATEGORY_CHOICES = [
    #     ('sanitation', 'Sanitation'),
    #     ('safety', 'Safety'),
    #     ('infrastructure', 'Infrastructure'),
    #     ('noise', 'Noise'),
    #     ('utilities', 'Utilities'),
    #     ('other', 'Other'),
    # ]

    # PRIORITY_CHOICES = [
    #     ('low', 'Low'),
    #     ('medium', 'Medium'),
    #     ('high', 'High'),
    #     ('urgent', 'Urgent'),
    # ]

    # STATUS_CHOICES = [
    #     ('pending', 'Pending'),
    #     ('in_progress', 'In Progress'),
    #     ('resolved', 'Resolved'),
    #     ('closed', 'Closed'),
    # ]

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

# Assistance Requests Table
class AssistanceRequest(models.Model):
    # TYPE_CHOICES = [
    #     ('medical', 'Medical'),
    #     ('financial', 'Financial'),
    #     ('legal', 'Legal'),
    #     ('emergency', 'Emergency'),
    #     ('social', 'Social'),
    #     ('other', 'Other'),
    # ]

    # URGENCY_CHOICES = [
    #     ('low', 'Low'),
    #     ('medium', 'Medium'),
    #     ('high', 'High'),
    #     ('critical', 'Critical'),
    # ]

    # STATUS_CHOICES = [
    #     ('pending', 'Pending'),
    #     ('approved', 'Approved'),
    #     ('in_progress', 'In Progress'),
    #     ('completed', 'Completed'),
    #     ('rejected', 'Rejected'),
    # ]

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


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='complaint_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class AssistanceAttachment(models.Model):
    assistance = models.ForeignKey(AssistanceRequest, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='assistance_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)