# tasks.py
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
import logging
import hashlib
from .models import DownloadToken, DrivePermission
from .utils import get_client_ip
from celery import shared_task  # For defining asynchronous tasks
from django.utils import timezone  # For handling timezone-aware datetime
from datetime import timedelta  # For handling time intervals
logger = logging.getLogger(__name__)



@shared_task
def cleanup_download_access(token_id):
    """Cleanup task for expired downloads"""
    from .views import GoogleDriveService
    
    try:
        token = DownloadToken.objects.get(id=token_id)
        if token.is_expired() or token.download_count >= token.max_downloads:
            # Revoke Drive access
            drive_service = GoogleDriveService()
            drive_service.revoke_access(
                token.purchase.drive_file.file_id,
                token.purchase.user.email
            )
            
            # Update token status
            token.revoke()
            
            logger.info(f"Cleaned up access for token {token.short_code}")
    except Exception as e:
        logger.error(f"Cleanup failed for token {token_id}: {str(e)}")

@shared_task
def monitor_drive_permissions():
    """Periodic task to monitor and cleanup Drive permissions"""
    active_permissions = DrivePermission.objects.filter(
        is_active=True,
        granted_at__lt=timezone.now() - timedelta(days=7)
    )
    for permission in active_permissions:
        cleanup_download_access.delay(permission.id)

# DriveFile model method implementation

def generate_download_url(self, user_email):
    """Generate secure download URL for the file"""
    from .views import GoogleDriveService
    try:
        # Check existing permission
        permission = DrivePermission.objects.filter(
            drive_file=self,
            email=user_email,
            is_active=True
        ).first()

        drive_service = GoogleDriveService()

        if not permission:
            # Grant new permission
            permission_id = drive_service.grant_access(self.file_id, user_email)
            
            # Record permission
            permission = DrivePermission.objects.create(
                drive_file=self,
                email=user_email,
                permission_id=permission_id,
                granting_ip=get_client_ip()
            )

        # Get download URL
        file = drive_service.service.files().get(
            fileId=self.file_id,
            fields='webContentLink'
        ).execute()

        # Update last access
        permission.last_access_timestamp = timezone.now()
        permission.save()

        return file.get('webContentLink')

    except Exception as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        raise