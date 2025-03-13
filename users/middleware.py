from django.utils.timezone import now
from .models import UserActivity, PageVisit
from collections import defaultdict
import re
from django.conf import settings

class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = now()
        response = self.get_response(request)  # Process request and get response

        # Skip tracking for excluded URLs or non-tracked paths
        if not self.should_track(request):
            return response

        # Ensure session is created
        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        # Retrieve or create a UserActivity record
        if request.user.is_authenticated:
            user = request.user
            activity, created = UserActivity.objects.get_or_create(
                user=user,
                session_id=session_key,
                defaults={'start_time': start_time}
            )
        else:
            user = None
            activity, created = UserActivity.objects.get_or_create(
                session_id=session_key,
                defaults={'start_time': start_time}
            )

        # Calculate time spent on the previous page (if any)
        last_page_visit = PageVisit.objects.filter(activity=activity).order_by('-timestamp').first()
        if last_page_visit:
            time_spent = (start_time - last_page_visit.timestamp).total_seconds()
            last_page_visit.duration = time_spent
            last_page_visit.save()

        # Record the current page visit
        PageVisit.objects.create(
            activity=activity,
            page_url=request.path,
            timestamp=start_time,
            duration=0,  # Duration will be updated on the next request
            method=request.method,
            status_code=response.status_code,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=self.get_client_ip(request)
        )

        # Update the last activity time
        activity.last_activity = now()
        activity.save()

        return response

    def should_track(self, request):
        """
        Determine if the request should be tracked based on URL patterns.
        """
        track_patterns = getattr(settings, 'TRACK_URLS', ['^/'])
        exclude_patterns = getattr(settings, 'EXCLUDE_URLS', [])
        return (
            any(re.match(pattern, request.path) for pattern in track_patterns) and
            not any(re.match(pattern, request.path) for pattern in exclude_patterns)
        )

    def get_client_ip(self, request):
        """Retrieve the IP address of the client making the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip