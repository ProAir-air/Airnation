import uuid
import re
import logging
import hashlib
import phonenumbers
import isodate


from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import (
    URLValidator,
    RegexValidator,
    MinLengthValidator,
    MaxLengthValidator,
    EmailValidator
)
from django.utils.translation import gettext_lazy as _

from googleapiclient.discovery import build
from phonenumber_field.modelfields import PhoneNumberField

from .patterns import drive_patterns
from .utils import get_client_ip

User = get_user_model()
logger = logging.getLogger(__name__)

# Create your models here.
DEVICE_TYPES = [
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('desktop', 'Desktop'),
        ('pc', 'PC'),
        ('smart_tv', 'Smart TV'),
        ('console', 'Gaming Console'),
        ('wearable', 'Wearable Device'),
        ('iot', 'IoT Device'),
        ('unknown', 'Unknown Device')
    ]

CATEGORY_CHOICES = [
        ('DAW', 'DAWs'),
        ('Plugins', 'Plugins'),
        ('Sample', 'Sample'),
        ('library','Library & Expansions')
    ]

class App(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=5000,null=True, blank=True)
    description = models.TextField(null=True,blank=True)
    thumbails=models.ImageField(upload_to='app_thumbnails', null=True, blank=True)
    category = models.CharField(max_length=5000, choices=CATEGORY_CHOICES, null=True, blank=True)

    # Video related fields
    video = models.FileField(upload_to='app_videos/', null=True, blank=True)
    video_size = models.FloatField(default=0)
    
    # YouTube related fields
    youtube_link = models.URLField(max_length=5000, null=True, blank=True)
    youtube_duration = models.DurationField(null=True, blank=True)
    youtube_comments_count = models.PositiveIntegerField(default=0)
    youtube_views_count = models.PositiveIntegerField(default=0)
    youtube_thumbnails = models.JSONField(null=True, blank=True)  # Store multiple thumbnail URLs
    
    # App and Drive related fields
    app_file = models.FileField(upload_to='app_files/', null=True, blank=True)
    google_drive_link = models.URLField(max_length=5000, null=True, blank=True)
    
     # Price related fields
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD', null=True, blank=True)

    # Status fields
    banned = models.BooleanField(default=False)
    send_notification = models.BooleanField(default=False)
    read = models.BooleanField(default=False)
    premium = models.BooleanField(default=False) 
    timestamp = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self):
        return reverse('apps:preview_app', kwargs={'pk': self.pk})

    def clean(self):
        # Call parent's clean method
        super().clean()
        
        # Validate YouTube link if provided
        if self.youtube_link:
            self.validate_youtube_link()
            
        # Validate Google Drive link if provided
        if self.google_drive_link:
            self.validate_drive_link()

    def validate_youtube_link(self):
        """Validate YouTube link format and extract video ID"""
        try:
            # Regular expressions for different YouTube URL formats
            youtube_regex = (
                r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
                r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
            )
            
            match = re.match(youtube_regex, self.youtube_link)
            
            if not match:
                raise ValidationError('Invalid YouTube URL format')
            
            self.video_id = match.group(6)
            
        except Exception as e:
            raise ValidationError(f'YouTube link validation error: {str(e)}')

    def validate_drive_link(self):
        """Validate Google Drive link format"""
        try:
            is_valid = any(re.match(pattern, self.google_drive_link) for pattern in drive_patterns)
            
            if not is_valid:
                raise ValidationError('Invalid Google Drive link format')
                
        except Exception as e:
            raise ValidationError(f'Google Drive link validation error: {str(e)}')

    def populate_youtube_data(self):
        """Populate YouTube metadata using YouTube API"""
        try:
            if not hasattr(self, 'video_id'):
                self.validate_youtube_link()

                """
                API="AIzaSyCJFxvWMfN5JORXyZ5POrrJK7kevivapmQ"
YOUTUBE_API_VERSION='v3'
YOUTUBE_API_SERVICE_NAME='youtube'
                """

            youtube = build(
                settings.YOUTUBE_API_SERVICE_NAME,
                settings.YOUTUBE_API_VERSION,
                developerKey=settings.API
            )

            # Request video details
            response = youtube.videos().list(
                id=self.video_id,
                part='snippet,contentDetails,statistics'
            ).execute()

            if not response.get('items'):
                raise ValidationError('YouTube video not found or is private')

            video_data = response['items'][0]

            # Extract and convert duration from ISO 8601 format
            duration_iso = video_data['contentDetails']['duration']
            self.youtube_duration = isodate.parse_duration(duration_iso)

            # Extract statistics
            statistics = video_data['statistics']
            self.youtube_views_count = int(statistics.get('viewCount', 0))
            self.youtube_comments_count = int(statistics.get('commentCount', 0))

            # Extract thumbnails
            thumbnails = video_data['snippet']['thumbnails']
            self.youtube_thumbnails = {
                'default': thumbnails.get('default', {}).get('url'),
                'medium': thumbnails.get('medium', {}).get('url'),
                'high': thumbnails.get('high', {}).get('url'),
                'standard': thumbnails.get('standard', {}).get('url'),
                'maxres': thumbnails.get('maxres', {}).get('url')
            }

        except Exception as e:
            raise ValidationError(f'Error fetching YouTube data: {str(e)}')

    def save(self, *args, **kwargs):
        # Handle video file size
        if self.video and hasattr(self.video, 'file'):
            self.video_size = self.video.file.size

        # Validate and populate YouTube data if link is provided
        if self.youtube_link:
            self.validate_youtube_link()
            self.populate_youtube_data()

        # Validate Google Drive link if provided
        if self.google_drive_link:
            self.validate_drive_link()

        self.premium = bool(self.amount)  # True if amount is not None, False if None or blank
        
        super().save(*args, **kwargs)    

class DriveFile(models.Model):
    """Stores Google Drive file information"""
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='drive_files')
    file_id = models.CharField(max_length=100)  # Google Drive File ID
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(default=0)  # Size in bytes
    mime_type = models.CharField(max_length=100)
    version = models.CharField(max_length=50, null=True, blank=True)  # File version tracking
    checksum = models.CharField(max_length=64, null=True, blank=True)  # File integrity check
    is_active = models.BooleanField(default=True)  # Whether file is available for download
    max_downloads_per_purchase = models.IntegerField(default=2)
    download_expiry_hours = models.IntegerField(default=24)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['file_id']),
            models.Index(fields=['is_active']),
        ]

    def get_client_ip(request):
        """Retrieve the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def generate_download_url(self, user_email):
        """Generate secure download URL for the file"""
        from .views import GoogleDriveService
        try:
            drive_service = GoogleDriveService()
            
            # Check existing permission
            permission = DrivePermission.objects.filter(
                drive_file=self,
                email=user_email,
                is_active=True
            ).first()

            if not permission:
                # Grant new permission
                permission_id = drive_service.grant_access(self.file_id, user_email)
                
                permission = DrivePermission.objects.create(
                    drive_file=self,
                    user=User.objects.get(email=user_email),
                    permission_id=permission_id,
                    email=user_email,
                    granting_ip=get_client_ip()
                )

            # Get download URL
            file = drive_service.service.files().get(
                fileId=self.file_id,
                fields='webContentLink,webViewLink'
            ).execute()

            # Update last access
            permission.last_access_timestamp = timezone.now()
            permission.save()

            # Return download URL with additional parameters
            download_url = file.get('webContentLink')
            if not download_url:
                download_url = file.get('webViewLink')

            # Add security token
            security_token = hashlib.sha256(
                f"{self.file_id}{user_email}{timezone.now().timestamp()}".encode()
            ).hexdigest()

            return f"{download_url}&security_token={security_token}"

        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            raise

    
        

class Purchase(models.Model):
    """Stores purchase, payment, and download information"""
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Payment Pending'),
        ('COMPLETED', 'Payment Completed'),
        ('FAILED', 'Payment Failed'),
        ('REFUNDED', 'Payment Refunded')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    app = models.ForeignKey(App, on_delete=models.SET_NULL, null=True)
    drive_file = models.ForeignKey(DriveFile, on_delete=models.SET_NULL, null=True)
    
    # Purchase identification
    purchase_id = models.UUIDField(default=uuid.uuid4, editable=False)
    purchase_date = models.DateTimeField(auto_now_add=True)
    
    # Payment information
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    payment_provider_ref = models.CharField(max_length=255, null=True, blank=True)  # Reference from payment provider
    
    # Transaction details
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Payment timestamps
    payment_initiated_at = models.DateTimeField(auto_now_add=True)
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    ip_address = models.CharField(max_length=50, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    # Meta information
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['purchase_id']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['payment_provider_ref']),
        ]

    def __str__(self):
        return f"Purchase {self.purchase_id} - {self.payment_status}"

    def mark_as_completed(self, payment_ref=None):
        """Mark the purchase as completed and record completion time"""
        self.payment_status = 'COMPLETED'
        self.payment_completed_at = timezone.now()
        if payment_ref:
            self.payment_provider_ref = payment_ref
        self.save()
        
        # Create download token after successful payment
        expiry_time = timezone.now() + timezone.timedelta(hours=24)  # 24 hour expiry
        DownloadToken.objects.create(
            purchase=self,
            short_code=uuid.uuid4().hex[:12],
            expiry_time=expiry_time,
            user_ip=self.ip_address
        )

    def mark_as_failed(self, payment_ref=None):
        """Mark the purchase as failed"""
        self.payment_status = 'FAILED'
        if payment_ref:
            self.payment_provider_ref = payment_ref
        self.save()

    def mark_as_refunded(self):
        """Mark the purchase as refunded"""
        self.payment_status = 'REFUNDED'
        self.save()
        
        # Deactivate any associated download tokens
        DownloadToken.objects.filter(purchase=self).update(is_active=False)

    def can_generate_download_token(self):
        """Check if purchase is eligible for download token generation"""
        return self.payment_status == 'COMPLETED'

    def get_active_download_token(self):
        """Get the active download token for this purchase"""
        return self.downloadtoken_set.filter(
            is_active=True,
            expiry_time__gt=timezone.now()
        ).first()

class DownloadToken(models.Model):
    """Manages download access and tracking"""
    DOWNLOAD_STATUS_CHOICES = [
        ('PENDING', 'Pending First Download'),
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('LIMIT_REACHED', 'Download Limit Reached'),
        ('REVOKED', 'Manually Revoked')
    ]

    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    short_code = models.CharField(max_length=50, unique=True)
    download_count = models.IntegerField(default=0)
    max_downloads = models.IntegerField(default=2)
    expiry_time = models.DateTimeField()
    user_ip = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=DOWNLOAD_STATUS_CHOICES,
        default='PENDING'
    )
    
    # Security tracking
    last_download_ip = models.CharField(max_length=50, null=True, blank=True)
    last_download_timestamp = models.DateTimeField(null=True, blank=True)
    last_download_user_agent = models.TextField(null=True, blank=True)
    
    # File version tracking
    file_version = models.CharField(max_length=50, null=True, blank=True)
    file_checksum = models.CharField(max_length=64, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['short_code']),
            models.Index(fields=['expiry_time']),
            models.Index(fields=['status']),
        ]

    def is_expired(self):
        return timezone.now() > self.expiry_time

    def can_download(self):
        return (
            self.is_active and
            not self.is_expired() and
            self.download_count < self.max_downloads and
            self.status in ['PENDING', 'ACTIVE']
        )

    def record_download(self, ip_address, user_agent):
        """Record a download attempt"""
        self.download_count += 1
        self.last_download_ip = ip_address
        self.last_download_user_agent = user_agent
        self.last_download_timestamp = timezone.now()
        
        if self.download_count >= self.max_downloads:
            self.status = 'LIMIT_REACHED'
        elif self.status == 'PENDING':
            self.status = 'ACTIVE'
            
        self.save()

    def revoke(self):
        """Revoke download access"""
        self.is_active = False
        self.status = 'REVOKED'
        self.save()


class DrivePermission(models.Model):
    """Tracks Google Drive permissions granted to users"""
    drive_file = models.ForeignKey(DriveFile, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    permission_id = models.CharField(max_length=100)  # Google Drive permission ID
    email = models.EmailField()  # Store email explicitly for tracking
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Additional security tracking
    granting_ip = models.CharField(max_length=50, null=True, blank=True)
    last_access_ip = models.CharField(max_length=50, null=True, blank=True)
    last_access_timestamp = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['permission_id']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]

    def revoke(self):
        """Revoke the Drive permission"""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save()

class AppViewHistory(models.Model):
    app = models.ForeignKey(App, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    viewer_ip = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=1)
    user_agent = models.TextField(null=True)
    session_id = models.CharField(max_length=1000, null=True)
    device_type = models.CharField(max_length=2000, choices=DEVICE_TYPES, null=True)
    browser = models.CharField(max_length=1000, null=True)
    os = models.CharField(max_length=1000, null=True)
    location = models.CharField(max_length=2000, null=True)

    class Meta:
        unique_together = ('app', 'viewer_ip', 'session_id', 'user')
        indexes = [
            models.Index(fields=['app', 'viewed_at']),
            models.Index(fields=['device_type']),
        ]

class AppDownloadHistory(models.Model):
    app = models.ForeignKey(App, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    session_id = models.CharField(max_length=1000, null=True)
    downloader_ip = models.GenericIPAddressField(null=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=1)
    file_size = models.FloatField(null=True)  # Size in bytes
    download_speed = models.FloatField(null=True)  # Average speed in bytes/second
    completion_status = models.BooleanField(default=True)  # Whether download completed successfully
    download_format = models.CharField(max_length=100, null=True)  # File extension
    
    is_visible = models.BooleanField(default=True)
    
    download_type = models.CharField(max_length=20, choices=[
        ('video', 'Video'),
        ('app', 'Application'),
        ('other', 'Other')
    ])
     # Device and platform info
    user_agent = models.TextField(null=True)
    device_type = models.CharField(max_length=200, choices=DEVICE_TYPES, null=True)
    browser = models.CharField(max_length=1000, null=True)
    os = models.CharField(max_length=1000, null=True)
    
    # Location info (can be populated from IP)
    country = models.CharField(max_length=1000, null=True)
    city = models.CharField(max_length=1000, null=True)
    

    class Meta:
        unique_together = ('app', 'user', 'session_id', 'downloader_ip')
        indexes = [
            models.Index(fields=['downloaded_at']),
            models.Index(fields=['device_type']),
            models.Index(fields=['download_format']),
        ]


class SavedApp(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    app = models.ForeignKey(App, on_delete=models.SET_NULL, null=True)
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'app')

class AppFeedback(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    app = models.ForeignKey(App, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(null=True, blank=True)
    feedback_date = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('app', 'user')

class SearchQuery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    query = models.CharField(max_length=500)  # The search query string
    results_count = models.PositiveIntegerField()
    model_used = models.CharField(max_length=100, null=True, blank=True)  # e.g., 'App'
    sort_by = models.CharField(max_length=50, null=True, blank=True)
    successful = models.BooleanField(default=True)
    execution_time = models.FloatField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['query', 'timestamp']),
        ]

class AppReaction(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
        ('neutral', 'Neutral'),
    ]
    
    app = models.ForeignKey(App, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('app', 'user')

class LinkClick(models.Model):
    LINK_TYPES = [
        ('youtube', 'YouTube'),
        ('drive', 'Google Drive'),
    ]
    
    app = models.ForeignKey(App, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    link_type = models.CharField(max_length=10, choices=LINK_TYPES)
    clicked_at = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, null=True)
    ip_address = models.GenericIPAddressField(null=True)
    success = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['app', 'link_type']),
            models.Index(fields=['clicked_at']),
        ]



class Feedback(models.Model):
    class FeedbackType(models.TextChoices):
        BUG = 'BUG', _('Bug Report')
        FEATURE = 'FEATURE', _('Feature Request')
        IMPROVEMENT = 'IMPROVEMENT', _('Improvement Suggestion')
        GENERAL = 'GENERAL', _('General Feedback')
        OTHER = 'OTHER', _('Other')

    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low')
        MEDIUM = 'MEDIUM', _('Medium')
        HIGH = 'HIGH', _('High')
        CRITICAL = 'CRITICAL', _('Critical')

    class Status(models.TextChoices):
        NEW = 'NEW', _('New')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        RESOLVED = 'RESOLVED', _('Resolved')
        CLOSED = 'CLOSED', _('Closed')
        REJECTED = 'REJECTED', _('Rejected')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='feedbacks'
    )
    subject = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(5)],
        help_text=_("Brief description of your feedback")
    )
    feedback_type = models.CharField(
        max_length=20,
        choices=FeedbackType.choices,
        default=FeedbackType.GENERAL
    )
    description = models.TextField(
        validators=[MinLengthValidator(10)],
        help_text=_("Detailed description of your feedback")
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )
    attachment = models.FileField(
        upload_to='feedback_attachments/%Y/%m/',
        null=True,
        blank=True,
        help_text=_("Upload any relevant files (screenshots, documents, etc.)")
    )
    email = models.EmailField(
        validators=[EmailValidator()],
        help_text=_("We'll use this to follow up with you")
    )
    browser_info = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Browser and system information")
    )
    url = models.URLField(
        null=True,
        blank=True,
        help_text=_("URL where the issue occurred")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_anonymous = models.BooleanField(
        default=False,
        help_text=_("Submit feedback anonymously")
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Feedback')
        verbose_name_plural = _('Feedbacks')
        indexes = [
            models.Index(fields=['feedback_type', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_feedback_type_display()} - {self.subject}"

    def get_absolute_url(self):
        return reverse('apps:feedback_detail', kwargs={'pk': self.pk})
        
    def save(self, *args, **kwargs):
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            from django.utils import timezone
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)

class FeedbackResponse(models.Model):
    feedback = models.ForeignKey(
        Feedback,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='feedback_responses'
    )
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_internal = models.BooleanField(
        default=False,
        help_text=_("Internal note visible only to staff")
    )

    class Meta:
        ordering = ['created_at']

class ApplicationRequest(models.Model):
    request = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True
    )

    app_name = models.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-_]+$',
                message="App name can only contain letters, numbers, spaces, hyphens, and underscores."
            )
        ]
    )

    description = models.TextField()
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)

    phone_number = PhoneNumberField(
        blank=True, 
        region=None,  # Allows dynamic region detection
        help_text="Enter phone number with country code (e.g., +1234567890)"
    )

    whatsapp_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,  # Allow empty WhatsApp field
        help_text="Enter a phone number or a WhatsApp link (e.g., +1234567890 or https://wa.me/1234567890)"
    )

    def clean(self):
        # Validate app_name length
        if len(self.app_name.strip()) < 3:
            raise ValidationError({'app_name': 'App name must be at least 3 characters long'})

        # Validate description length
        if len(self.description.strip()) < 10:
            raise ValidationError({'description': 'Description must be at least 10 characters long'})

        # Validate WhatsApp field
        if self.whatsapp_number:
            if self.whatsapp_number.startswith("http"):
                # Validate as URL
                URLValidator()(self.whatsapp_number)
            else:
                # Validate as a phone number
                try:
                    phone_obj = phonenumbers.parse(self.whatsapp_number, None)  # Detect region dynamically
                    if not phonenumbers.is_valid_number(phone_obj):
                        raise ValidationError({'whatsapp_number': 'Invalid WhatsApp number'})
                    # Format number to E.164
                    self.whatsapp_number = phonenumbers.format_number(
                        phone_obj, phonenumbers.PhoneNumberFormat.E164
                    )
                except phonenumbers.NumberParseException:
                    raise ValidationError({'whatsapp_number': 'Invalid WhatsApp number format'})

    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.app_name} - {self.timestamp}"


class AdminResponse(models.Model):
    """Model where admin responds to requests"""
    request = models.OneToOneField(ApplicationRequest, on_delete=models.CASCADE)  # One response per request
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,related_name="admin_responses")  # Admin who answered
    response_text = models.TextField()  # Admin's response
    response_link = models.URLField(blank=True, null=True)  # Optional link
    is_visible = models.BooleanField(default=False)  # Whether users can see the response
    responded_at = models.DateTimeField(auto_now=True)  # Automatically updates on save

    def __str__(self):
        return f"Response to {self.request.app_name} by {self.admin.username if self.admin else 'Admin'}"
    

class NotificationComment(models.Model):
    app = models.ForeignKey('App', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.user.username} on {self.app.title}'    