import re
import uuid
import hashlib
import isodate
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from googleapiclient.discovery import build

from apps.patterns import drive_patterns
from apps.models import CATEGORY_CHOICES

class NotificationPost(models.Model):
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
    
    # Status fields
    send_notification = models.BooleanField(default=False)
    read = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ['-created_at']

    def get_thumbnail_url(self):
        """Returns the thumbnail URL if it exists, otherwise None"""
        return self.thumbnail.url if self.thumbnail else None

    @classmethod
    def get_next_unseen_notification(cls, user, seen_post_ids=None):
        """
        Get the next unseen notification for a user
        """
        seen_post_ids = seen_post_ids or []
        return cls.objects.filter(
            is_active=True
        ).exclude(
            id__in=seen_post_ids
        ).first()



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
 
        super().save(*args, **kwargs)

class NotificationInteraction(models.Model):
    """
    Simplified interaction model that combines all interaction types
    """
    INTERACTION_TYPES = (
        ('shown', 'Shown'),
        ('closed', 'Closed'),
        ('clicked', 'Clicked'),
        ('auto_closed', 'Auto Closed'),
    )

    post = models.ForeignKey(
        NotificationPost, 
        on_delete=models.CASCADE, 
        related_name='interactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    interaction_type = models.CharField(
        max_length=20, 
        choices=INTERACTION_TYPES
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['post', 'user', 'interaction_type']),
        ]

    @classmethod
    def record_interaction(cls, post, user, interaction_type):
        """
        Record a new interaction
        """
        return cls.objects.create(
            post=post,
            user=user,
            interaction_type=interaction_type
        )

