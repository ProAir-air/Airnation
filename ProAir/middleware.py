

# middleware.py
from django.utils.deprecation import MiddlewareMixin
from .models import NotificationPost, NotificationInteraction

class NotificationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            return

        # Get or initialize session data
        session_data = self._get_session_data(request)
        
        # Check if we should show a notification
        if not self._should_show_notification(session_data):
            return

        # Get next unseen notification
        notification = self._get_next_notification(request.user, session_data)
        if not notification:
            return

        # Update session and record interaction
        self._update_session(request, notification, session_data)
        self._record_interaction(notification, request.user)

    def _get_session_data(self, request):
        """Get or initialize notification session data"""
        return {
            'seen_posts': request.session.get('seen_notifications', []),
            'last_shown': request.session.get('last_notification_time', 0)
        }

    def _should_show_notification(self, session_data):
        """
        Determine if we should show a notification
        Add your custom logic here (e.g., timing between notifications)
        """
        return True

    def _get_next_notification(self, user, session_data):
        """Get the next unseen notification"""
        return NotificationPost.get_next_unseen_notification(
            user, 
            session_data['seen_posts']
        )

    def _update_session(self, request, notification, session_data):
        """Update session with new notification data"""
        # Update seen posts
        seen_posts = session_data['seen_posts']
        seen_posts.append(notification.id)
        request.session['seen_notifications'] = seen_posts

        # Set current notification
        request.session['current_notification'] = {
            'id': notification.id,
            'title': notification.title,
            'thumbnail': notification.get_thumbnail_url()
        }

        request.session.modified = True

    def _record_interaction(self, notification, user):
        """Record the notification shown interaction"""
        NotificationInteraction.record_interaction(
            post=notification,
            user=user,
            interaction_type='shown'
        )