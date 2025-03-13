import re
import time
import os
import json
import logging
import hashlib
import mimetypes
from datetime import timedelta
from django.utils.timezone import now
from functools import wraps

from django.db.models import (
    Sum,
    Count,
    Q,
    F,
    Avg,
    Exists,
    OuterRef
)
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView
)
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin
)
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)
from django.http import (
    JsonResponse,
    FileResponse,
    HttpResponseForbidden,
    HttpResponseRedirect
)
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.conf import settings

from google.oauth2 import service_account
from googleapiclient.discovery import build
from user_agents import parse

from .models import (
    App,
    CATEGORY_CHOICES,
    Purchase,
    DownloadToken,
    Feedback,
    FeedbackResponse,
    ApplicationRequest,
    AdminResponse,
    SavedApp,
    LinkClick,
    AppReaction,
    AppFeedback,
    AppViewHistory,
    AppDownloadHistory,SearchQuery
)
from .forms import (
    AppUploadForm,
    ApplicationRequestForm,
    FeedbackForm,
    FeedbackResponseForm,
    AdminResponseForm,
    NotificationCommentForm
)
from .utils import (
    submit_pesapal_order_request,
    generate_short_code,
    calculate_expiry_time,
    get_client_ip,validate_ip_address
)
from .tasks import cleanup_download_access
from ProAir.permission import StaffAndAdminRequiredMixin,staff_admin_required


logger = logging.getLogger(__name__)
class UserAppsListView(LoginRequiredMixin, StaffAndAdminRequiredMixin,ListView):
    model = App
    template_name = 'apps/user_apps_list.html'
    context_object_name = 'apps'
    paginate_by = 10

    def get_queryset(self):
        queryset = App.objects.filter(author=self.request.user)

        # Annotate with additional fields
        queryset = queryset.annotate(
            total_views=Count('appviewhistory'),
            total_downloads=Count('appdownloadhistory'),
            average_rating=Avg('appfeedback__rating'),
            total_likes=Count(
                'appreaction',
                filter=Q(appreaction__reaction='like')
            ),
            total_saves=Count('savedapp')
        ).order_by('-timestamp')

        # Apply time-based filtering
        time_value = self.request.GET.get('time_value')
        time_unit = self.request.GET.get('time_unit')
        if time_value and time_unit:
            try:
                time_value = int(time_value)
                time_delta = self.get_time_delta(time_value, time_unit)
                if time_delta:
                    queryset = queryset.filter(timestamp__gte=now() - time_delta)
            except ValueError:
                pass  # Ignore invalid input for filtering

        return queryset

    def get_time_delta(self, value, unit):
        """Convert value and unit to a timedelta."""
        if unit == "seconds":
            return timedelta(seconds=value)
        elif unit == "minutes":
            return timedelta(minutes=value)
        elif unit == "hours":
            return timedelta(hours=value)
        elif unit == "days":
            return timedelta(days=value)
        elif unit == "weeks":
            return timedelta(weeks=value)
        elif unit == "months":
            return timedelta(days=value * 30)  # Approximation
        elif unit == "years":
            return timedelta(days=value * 365)  # Approximation
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_apps'] = self.get_queryset().count()
        context['time_units'] = [
            ('seconds', 'Seconds'),
            ('minutes', 'Minutes'),
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months'),
            ('years', 'Years'),
        ]
        return context

    

class AppUploadView(LoginRequiredMixin, StaffAndAdminRequiredMixin,CreateView):
    model = App
    form_class = AppUploadForm
    template_name = 'apps/app_upload.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'pk': self.object.pk,
            })
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('apps:preview_app', kwargs={'pk': self.object.pk})
    

class AppPreviewView(LoginRequiredMixin,StaffAndAdminRequiredMixin,DetailView):
    model = App
    template_name = 'apps/app_preview.html'
    context_object_name = 'app'

    def get_queryset(self):
        return App.objects.filter(pk=self.kwargs['pk'])


class AppUpdateView(LoginRequiredMixin, StaffAndAdminRequiredMixin,UserPassesTestMixin, UpdateView):
    model = App
    form_class = AppUploadForm
    template_name = 'apps/app_edit.html'
    
    def test_func(self):
        app = self.get_object()
        return self.request.user == app.author
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'pk': self.object.pk
            })
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()
    
class AppDeleteView(LoginRequiredMixin, StaffAndAdminRequiredMixin,UserPassesTestMixin, DeleteView):
    model = App
    template_name =  'apps/app_confirm_delete.html'
    success_url = reverse_lazy('apps:app_list')  # Assuming you have an app_list view
    
    def test_func(self):
        app = self.get_object()
        return self.request.user == app.author

class AppListView(LoginRequiredMixin,ListView):
    model = App
    template_name = 'apps/list.html'
    context_object_name = 'apps'
    paginate_by = 10

    def get_queryset(self):
        start_time = time.time()
        queryset = App.objects.select_related('author')
        
        # Count unique views in the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        queryset = queryset.annotate(
            view_count=Count(
                'appviewhistory',
                filter=Q(
                    appviewhistory__viewed_at__gte=thirty_days_ago,
                ),
                distinct=True
            ),
            download_count=Sum('appdownloadhistory__download_count'),
            save_count=Count('savedapp', distinct=True)
        )

        # Get search query
        query = self.request.GET.get('q')
        sort_by = self.request.GET.get('sort_by')
        category_filter = self.request.GET.get('category', 'all')
        

        # Only process search history if there's a valid query
        if query:
            # Retrieve past search queries from cache
            search_history_key = f"search_history_{self.request.user.id if self.request.user.is_authenticated else 'guest'}"
            search_history = cache.get(search_history_key, [])
            
            # Remove the query if it exists and add it to the end (most recent)
            if query in search_history:
                search_history.remove(query)
            search_history.append(query)
            
            # Keep only the last 10 searches
            search_history = search_history[-10:]
            
            # Update cache with new search history
            cache.set(search_history_key, search_history, timeout=86400)  # Cache for 24 hours

            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(author__username__icontains=query)
            )
          # Filter by category (excluding 'all')
        if category_filter and category_filter != "all":
            queryset = queryset.filter(category=category_filter)
    
            # Track search history (assuming SearchQuery model exists)
            execution_time = time.time() - start_time
            search_data = {
                'query': query,
                'results_count': queryset.count(),
                'model_used': 'App',
                'sort_by': sort_by,
                'successful': queryset.exists(),
                'execution_time': execution_time,
                'user_agent': self.request.META.get('HTTP_USER_AGENT'),
                'ip_address': self.request.META.get('REMOTE_ADDR'),
            }

            if self.request.user.is_authenticated:
                search_data['user'] = self.request.user
            else:
                search_data['session_id'] = self.request.session.session_key

            SearchQuery.objects.create(**search_data)

        # Apply sorting
        if sort_by == 'popular':
            queryset = queryset.order_by('-save_count')
        elif sort_by == 'downloads':
            queryset = queryset.order_by('-download_count')
        elif sort_by == 'recent':
            queryset = queryset.order_by('-timestamp')
        else:
            queryset = queryset.order_by('-timestamp')
            
        queryset = queryset.filter(banned=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_sort'] = self.request.GET.get('sort_by')
        context['categories'] = dict(CATEGORY_CHOICES[:])  # Limit to first 5 categories
        
        context['selected_category'] = self.request.GET.get('category', 'all')  # Preserve selected category
        search_history_key = f"search_history_{self.request.user.id if self.request.user.is_authenticated else 'guest'}"
        context['search_history'] = cache.get(search_history_key, [])
    
        if self.request.user.is_authenticated:
            saved_apps = SavedApp.objects.filter(
                user=self.request.user
            ).values_list('app_id', flat=True)
            context['saved_apps'] = set(saved_apps)
            
        context['base_url'] = self.request.build_absolute_uri('/')[:-1]
        search_query = self.request.GET.get('q')
        if search_query:
            context['search_query'] = search_query
            context['total_results'] = self.get_queryset().count()  # Add total results count
            
        return context

class ViewTracker:
    BOT_PATTERNS = [
        r'bot', r'crawler', r'spider', r'slurp', r'wget', r'curl',
        r'favicon', r'facebook', r'embedly', r'quora', r'outbrain'
    ]
    
    @staticmethod
    def is_bot(user_agent):
        if not user_agent:
            return True
        user_agent_lower = user_agent.lower()
        return any(re.search(pattern, user_agent_lower) for pattern in ViewTracker.BOT_PATTERNS)

    @staticmethod
    def get_device_info(user_agent_string):
        try:
            user_agent = parse(user_agent_string)
            return {
                'browser': f"{user_agent.browser.family} {user_agent.browser.version_string}",
                'os': f"{user_agent.os.family} {user_agent.os.version_string}",
                'device_type': (
                    'mobile' if user_agent.is_mobile
                    else 'tablet' if user_agent.is_tablet
                    else 'desktop'
                )
            }
        except:
            return None

class AppDetailView(LoginRequiredMixin, DetailView):
    model = App
    template_name = 'apps/app_detail.html'
    context_object_name = 'app'

    COOLDOWN_PERIODS = {
        'default': 300,
        'video': 600,
        'premium': 1800,
    }

    def get_cooldown_period(self):
        if hasattr(self.object, 'content_type'):
            return self.COOLDOWN_PERIODS.get(
                self.object.content_type,
                self.COOLDOWN_PERIODS['default']
            )
        return self.COOLDOWN_PERIODS['default']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        is_saved = SavedApp.objects.filter(
            user=self.request.user,
            app=self.object
        ).exists()

        
        # Check if the user has already reacted
        user_has_reacted = AppReaction.objects.filter(
            app=self.object,
            user=self.request.user
        ).exists()

        # Check if the user has already provided feedback
        user_has_feedback = AppFeedback.objects.filter(
            app=self.object,
            user=self.request.user
        ).exists()

        # Get reaction counts
        reaction_counts = AppReaction.objects.filter(app=self.object).aggregate(
            like_count=Count('id', filter=Q(reaction='like')),
            dislike_count=Count('id', filter=Q(reaction='dislike')),
            neutral_count=Count('id', filter=Q(reaction='neutral'))
        )

        thirty_days_ago = timezone.now() - timedelta(days=30)
        view_stats = AppViewHistory.objects.filter(
            app=self.object,
            viewed_at__gte=thirty_days_ago
        ).aggregate(
            total_views=Count('id'),
            mobile_views=Count('id', filter=Q(device_type='mobile')),
            desktop_views=Count('id', filter=Q(device_type='desktop')),
            tablet_views=Count('id', filter=Q(device_type='tablet'))
        )

        download_stats = AppDownloadHistory.objects.filter(
            app=self.object
        ).aggregate(
            total_downloads=Count('id'),
            video_downloads=Count('id', filter=Q(download_type='video')),
            app_downloads=Count('id', filter=Q(download_type='app')),
            other_downloads=Count('id', filter=Q(download_type='other'))
        )

        context.update({
            'is_saved': is_saved,
            'view_stats': view_stats,
            'download_stats': download_stats,
            'youtube_stats': {
                'views': self.object.youtube_views_count,
             } if self.object.youtube_link else None,
            'user_has_reacted': user_has_reacted,
            'user_has_feedback': user_has_feedback,
            'like_count': reaction_counts['like_count'],
            'dislike_count': reaction_counts['dislike_count'],
            'neutral_count': reaction_counts['neutral_count'],
        })
        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        if not request.session.session_key:
            request.session.create()
        
        current_time = timezone.now()
        viewer_ip = request.META.get('REMOTE_ADDR')
        session_id = request.session.session_key
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')

        is_bot = ViewTracker.is_bot(user_agent_string)
        if is_bot:
            return response

        device_info = ViewTracker.get_device_info(user_agent_string)
        
        try:
            view_history = AppViewHistory.objects.select_for_update().get(
                app=self.object,
                viewer_ip=viewer_ip,
                session_id=session_id,
                user=request.user if request.user.is_authenticated else None
            )
            
            cooldown_period = self.get_cooldown_period()
            if (current_time - view_history.viewed_at).total_seconds() > cooldown_period:
                view_history.view_count = F('view_count') + 1
                view_history.user_agent = user_agent_string
                if device_info:
                    view_history.device_type = device_info['device_type']
                    view_history.browser = device_info['browser']
                    view_history.os = device_info['os']
                view_history.save()
        
        except AppViewHistory.DoesNotExist:
            AppViewHistory.objects.create(
                app=self.object,
                viewer_ip=viewer_ip,
                session_id=session_id,
                user_agent=user_agent_string,
                device_type=device_info['device_type'] if device_info else None,
                browser=device_info['browser'] if device_info else None,
                os=device_info['os'] if device_info else None,
                user=request.user if request.user.is_authenticated else None
            )
        return response

def track_download_speed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        response = func(*args, **kwargs)
        if hasattr(response, 'download_id'):
            download_time = time.time() - start_time
            if download_time > 0:
                AppDownloadHistory.objects.filter(id=response.download_id).update(
                    download_speed=response.file_size / download_time
                )
        return response
    return wrapper

@login_required
@track_download_speed
def download_app(request, pk):
    app = get_object_or_404(App, pk=pk)
    
    # Determine download type and file
    if request.GET.get('type') == 'video' and app.video:
        file_field = app.video
        download_type = 'video'
    elif app.app_file:
        file_field = app.app_file
        download_type = 'app'
    else:
        return JsonResponse({'error': 'No file available for download'}, status=400)

    device_info = ViewTracker.get_device_info(request.META.get('HTTP_USER_AGENT', ''))
    
    # Get file information
    try:
        file_size = file_field.size
        mime_type, _ = mimetypes.guess_type(file_field.path)
        file_format = os.path.splitext(file_field.name)[1][1:].lower()
    except:
        return JsonResponse({'error': 'Unable to process file'}, status=500)

    # Create download history
    download_history = AppDownloadHistory.objects.create(
        app=app,
        user=request.user,
        session_id=request.session.session_key,
        downloader_ip=request.META.get('REMOTE_ADDR'),
        file_size=file_size,
        download_type=download_type,
        download_format=file_format,
        user_agent=request.META.get('HTTP_USER_AGENT'),
        device_type=device_info['device_type'] if device_info else None,
        browser=device_info['browser'] if device_info else None,
        os=device_info['os'] if device_info else None
    )

    response = FileResponse(
        file_field.open('rb'),
        as_attachment=True,
        content_type=mime_type
    )
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_field.name)}"'
    response['Content-Length'] = file_size
    
    response.download_id = download_history.id
    response.file_size = file_size

    return response


class SavedAppListView(LoginRequiredMixin, ListView):
    model = SavedApp
    template_name = 'apps/saved_apps.html'
    context_object_name = 'saved_apps'


@login_required
@require_POST
def toggle_save_app(request, pk):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        app = get_object_or_404(App, pk=pk)
        saved, created = SavedApp.objects.get_or_create(
            user=request.user,
            app=app
        )
        if not created:
            saved.delete()
            return JsonResponse({'status': 'unsaved'})
        return JsonResponse({'status': 'saved'})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@require_POST
def delete_saved_app(request, id):
    """Deletes a saved app for the authenticated user via AJAX."""
    
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    saved_app = get_object_or_404(SavedApp, id=id, user=request.user)
    
    saved_app.delete()
    
    return JsonResponse({'status': 'success', 'app_id': id})


@login_required
def download_history(request):
    history = AppDownloadHistory.objects.all()

    history_with_metrics = []
    for item in history:
        total_views = AppViewHistory.objects.filter(
            app=item.app
        ).count()

        total_saves = SavedApp.objects.filter(
            app=item.app
        ).count()

        total_downloads = AppDownloadHistory.objects.filter(
            app=item.app
        ).count()

        history_with_metrics.append({
            'history_item': item,
            'total_views': total_views,
            'total_saves': total_saves,
            'total_downloads': total_downloads,
            'download_type': item.download_type,
            'file_size': item.file_size,
            'download_speed': item.download_speed
        })

    return render(request, 'apps/download_history.html', {
        'history': history_with_metrics
    })


@login_required
def remove_download_history(request, history_id):
    if request.method == 'POST':
        history_item = get_object_or_404(
            AppDownloadHistory, 
            id=history_id, 
            user=request.user
        )
        history_item.is_visible = False
        history_item.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def track_link_click(request):
    if request.method == 'POST':
        app_id = request.POST.get('app_id')
        link_type = request.POST.get('link_type')
        
        app = get_object_or_404(App, id=app_id)
        
        # Create link click record
        LinkClick.objects.create(
            app=app,
            user=request.user,
            link_type=link_type,
            ip_address=request.META.get('REMOTE_ADDR'),
            session_id=request.session.session_key
        )
        
        # Get total clicks for this link type
        total_clicks = LinkClick.objects.filter(
            app=app,
            link_type=link_type
        ).count()
        
        return JsonResponse({'status': 'success', 'total_clicks': total_clicks})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def handle_reaction(request):
    if request.method == 'POST':
        app_id = request.POST.get('app_id')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        app = get_object_or_404(App, id=app_id)
        
        # Create or update feedback
        AppFeedback.objects.update_or_create(
            app=app,
            user=request.user,
            defaults={'rating': rating, 'comment': comment}
        )
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def submit_feedback(request):
    if request.method == 'POST':
        app_id = request.POST.get('app_id')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        app = get_object_or_404(App, id=app_id)
        
        # Update or create feedback
        AppFeedback.objects.update_or_create(
            app=app,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        
        # Calculate average rating
        avg_rating = AppFeedback.objects.filter(app=app).aggregate(
            Avg('rating')
        )['rating__avg'] or 0
        
        return JsonResponse({
            'status': 'success',
            'avg_rating': round(avg_rating, 1)
        })
    return JsonResponse({'status': 'error'}, status=400)


class FeedbackCreateView(LoginRequiredMixin,CreateView):
    model = Feedback
    form_class = FeedbackForm
    template_name = 'apps/feedback_form.html'
    

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Collect browser information
        if self.request.headers.get('User-Agent'):
            form.instance.browser_info = {
                'user_agent': self.request.headers.get('User-Agent'),
                'remote_addr': self.request.META.get('REMOTE_ADDR'),
            }
        response = super().form_valid(form)
        messages.success(self.request, 'Thank you for your feedback!')
        return response
    
    def get_success_url(self):
        return self.object.get_absolute_url()


class FeedbackListView(LoginRequiredMixin,StaffAndAdminRequiredMixin, ListView):
    model = Feedback
    template_name = 'apps/feedback_list.html'
    context_object_name = 'feedbacks'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset


class FeedbackDetailView(LoginRequiredMixin, DetailView):
    model = Feedback
    template_name = 'apps/feedback_detail.html'
    context_object_name = 'feedback'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['response_form'] = FeedbackResponseForm()
        return context

    def post(self, request, *args, **kwargs):
        """Handles the response form submission"""
        feedback = self.get_object()
        form = FeedbackResponseForm(request.POST)

        if form.is_valid():
            response = form.save(commit=False)
            response.feedback = feedback
            response.responder = request.user  # Assign the current user
            response.save()
            return redirect(feedback.get_absolute_url())  # Redirect back to the detail page

        return self.get(request, *args, **kwargs)  # Re-render the page with errors


class FeedbackResponseCreateView(LoginRequiredMixin,StaffAndAdminRequiredMixin, CreateView):
    model = FeedbackResponse
    form_class = FeedbackResponseForm

    def form_valid(self, form):
        form.instance.feedback = get_object_or_404(Feedback, pk=self.kwargs['pk'])
        form.instance.responder = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.feedback.get_absolute_url()


class FeedbackUpdateView(LoginRequiredMixin,StaffAndAdminRequiredMixin, UpdateView):
    model = Feedback
    form_class = FeedbackForm
    template_name = 'apps/feedback_update.html'
    
    def get_success_url(self):
        return reverse_lazy('apps:feedback_detail', kwargs={'pk': self.object.pk})
    

class ApplicationRequestCreateView(LoginRequiredMixin, CreateView):
    model = ApplicationRequest
    form_class = ApplicationRequestForm
    template_name = 'apps/application_request_form.html'
    success_url = reverse_lazy('apps:user_requests')
    
    def form_valid(self, form):
        form.instance.request = self.request.user
        form.instance.ip_address = self.get_client_ip()
        return super().form_valid(form)
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class UserRequestsView(LoginRequiredMixin, ListView):
    """Displays the user's application requests and admin responses"""
    model = ApplicationRequest
    template_name = "apps/user_requests.html"
    context_object_name = "requests"

    def get_queryset(self):
        """Return only requests belonging to the logged-in user"""
        return ApplicationRequest.objects.filter(request=self.request.user).prefetch_related("adminresponse")


class UnrespondedRequestsView(LoginRequiredMixin,StaffAndAdminRequiredMixin, UserPassesTestMixin, ListView):
    model = ApplicationRequest
    template_name = "apps/unresponded_requests.html"
    context_object_name = "requests"
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        return ApplicationRequest.objects.filter(
            adminresponse__isnull=True
        ).order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = {
            'unresponded_count': ApplicationRequest.objects.filter(
                adminresponse__isnull=True).count(),
            'responded_count': ApplicationRequest.objects.filter(
                adminresponse__isnull=False).count(),
            'total_requests': ApplicationRequest.objects.count(),
        }
        context.update(stats)
        return context

class RespondedRequestsView(LoginRequiredMixin,StaffAndAdminRequiredMixin, UserPassesTestMixin, ListView):
    model = ApplicationRequest
    template_name = "apps/responded_requests.html"
    context_object_name = "requests"
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        return ApplicationRequest.objects.filter(
            adminresponse__isnull=False
        ).order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = {
            'unresponded_count': ApplicationRequest.objects.filter(
                adminresponse__isnull=True).count(),
            'responded_count': ApplicationRequest.objects.filter(
                adminresponse__isnull=False).count(),
            'total_requests': ApplicationRequest.objects.count(),
        }
        context.update(stats)
        return context

class AllRequestsOverviewView(LoginRequiredMixin,StaffAndAdminRequiredMixin, UserPassesTestMixin, ListView):
    model = ApplicationRequest
    template_name = "apps/all_requests.html"
    context_object_name = "requests"
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        return ApplicationRequest.objects.all().order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = {
            'unresponded_count': ApplicationRequest.objects.filter(
                adminresponse__isnull=True).count(),
            'responded_count': ApplicationRequest.objects.filter(
                adminresponse__isnull=False).count(),
            'total_requests': ApplicationRequest.objects.count(),
        }
        context.update(stats)
        return context

class AdminRespondView(LoginRequiredMixin, StaffAndAdminRequiredMixin,UserPassesTestMixin, UpdateView):
    """Allows admin to answer a request"""
    model = AdminResponse
    form_class = AdminResponseForm
    template_name = "apps/admin_response_form.html"
    success_url = reverse_lazy("apps:responded_requests") 

    def test_func(self):
        """Restrict view to admin users only"""
        return self.request.user.is_staff

    def get_object(self, queryset=None):
        """Ensure an AdminResponse exists before answering"""
        app_request = get_object_or_404(ApplicationRequest, id=self.kwargs["request_id"])
        response, created = AdminResponse.objects.get_or_create(request=app_request, defaults={"admin": self.request.user})
        return response


class NotificationListView(LoginRequiredMixin, ListView):
    model = App
    template_name = 'apps/notification_list.html'
    context_object_name = 'notifications'
    
    def get_queryset(self):
        return App.objects.filter(send_notification=True).order_by('-id')


class NotificationDetailView(LoginRequiredMixin, DetailView):
    model = App
    template_name = 'apps/notification_detail.html'
    context_object_name = 'notification'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = NotificationCommentForm()
        context['comments'] = self.object.comments.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = NotificationCommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.app = self.object
            comment.user = request.user
            comment.save()
            messages.success(request, 'Comment added successfully!')
            return redirect('apps:notification_detail', pk=self.object.pk)
        
        context = self.get_context_data(object=self.object)
        context['comment_form'] = form
        return self.render_to_response(context)

    def get_object(self):
        obj = super().get_object()
        if not obj.read:
            obj.read = True
            obj.save()
        return obj

@login_required
def mark_notifications_read(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required'})
    
    notification_ids = request.POST.getlist('notification_ids[]')
    
    if notification_ids:
        App.objects.filter(
            id__in=notification_ids,
            send_notification=True,
            read=False
        ).update(read=True)
        return JsonResponse({'status': 'success', 'message': 'Notifications marked as read'})
    
    return JsonResponse({'status': 'error', 'message': 'No notifications selected'})
@login_required
def mark_all_read(request):
    if request.user.is_authenticated:
        App.objects.filter(send_notification=True, read=False).update(read=True)
    return HttpResponseRedirect(reverse('apps:notification_list'))


class DashboardView(LoginRequiredMixin, StaffAndAdminRequiredMixin,TemplateView):
    template_name = 'apps/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all counts
        context['total_apps'] = App.objects.count()
        context['total_notifications'] = App.objects.filter(send_notification=True).count()
        context['total_read'] = App.objects.filter(read=True).count()
        context['total_unread'] = App.objects.filter(read=False).count()
        context['total_unsent'] = App.objects.filter(send_notification=False).count()
        
        return context


class SentNotificationsView(LoginRequiredMixin, StaffAndAdminRequiredMixin,ListView):
    template_name = 'apps/sent_notifications.html'
    context_object_name = 'apps'
    
    def get_queryset(self):
        return App.objects.filter(send_notification=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_apps'] = App.objects.count()
        context['total_notifications'] = App.objects.filter(send_notification=True).count()
        context['total_read'] = App.objects.filter(read=True).count()
        context['total_unread'] = App.objects.filter(read=False).count()
        context['total_unsent'] = App.objects.filter(send_notification=False).count()
        return context

class UnsentNotificationListView(LoginRequiredMixin,StaffAndAdminRequiredMixin, ListView):
    template_name = 'apps/unsent_notifications.html'
    context_object_name = 'apps'
    
    def get_queryset(self):
        return App.objects.filter(send_notification=False)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add statistics to context
        context['total_apps'] = App.objects.count()
        context['total_notifications'] = App.objects.filter(send_notification=True).count()
        context['total_read'] = App.objects.filter(read=True).count()
        context['total_unread'] = App.objects.filter(read=False).count()
        context['total_unsent'] = App.objects.filter(send_notification=False).count()
        return context

class UpdateNotificationStatusView(LoginRequiredMixin,StaffAndAdminRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        app_id = request.POST.get('app_id')
        try:
            app = App.objects.get(id=app_id)
            app.send_notification = True
            app.save()
            return JsonResponse({'status': 'success'})
        except App.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'App not found'}, status=404)



class UnrespondedFeedbackView(LoginRequiredMixin,StaffAndAdminRequiredMixin, ListView):
    model = Feedback
    template_name = 'apps/unresponded_feedback_list.html'
    context_object_name = 'feedbacks'
    paginate_by = 10

    def get_queryset(self):
        return Feedback.objects.exclude(
            responses__is_internal=False
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get overview statistics
        total_feedback = Feedback.objects.count()
        responded_count = Feedback.objects.filter(
            responses__is_internal=False
        ).distinct().count()
        unresponded_count = total_feedback - responded_count

        # Add statistics to context
        context.update({
            'total_feedback': total_feedback,
            'responded_count': responded_count,
            'unresponded_count': unresponded_count,
            'section_title': 'Unresponded Feedback',
            'feedback_type_stats': Feedback.objects.exclude(
                responses__is_internal=False
            ).values('feedback_type').annotate(count=Count('id'))
        })
        return context

class RespondedFeedbackView(LoginRequiredMixin, StaffAndAdminRequiredMixin,ListView):
    model = Feedback
    template_name = 'apps/responded_feedback_list.html'
    context_object_name = 'feedbacks'
    paginate_by = 10

    def get_queryset(self):
        return Feedback.objects.filter(
            responses__is_internal=False
        ).distinct().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get overview statistics
        total_feedback = Feedback.objects.count()
        responded_count = Feedback.objects.filter(
            responses__is_internal=False
        ).distinct().count()
        unresponded_count = total_feedback - responded_count

        # Add statistics to context
        context.update({
            'total_feedback': total_feedback,
            'responded_count': responded_count,
            'unresponded_count': unresponded_count,
            'section_title': 'Responded Feedback',
            'feedback_type_stats': Feedback.objects.filter(
                responses__is_internal=False
            ).values('feedback_type').annotate(count=Count('id'))
        })
        return context


class AllFeedbackView(LoginRequiredMixin,StaffAndAdminRequiredMixin, ListView):
    model = Feedback
    template_name = 'apps/all_feedback_list.html'
    context_object_name = 'feedbacks'
    paginate_by = 10

    def get_queryset(self):
        queryset = Feedback.objects.all().order_by('-created_at')
        # Annotate with response information
        queryset = queryset.annotate(
            has_public_response=Exists(
                FeedbackResponse.objects.filter(
                    feedback=OuterRef('pk'),
                    is_internal=False
                )
            )
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get overview statistics
        total_feedback = Feedback.objects.count()
        responded_count = Feedback.objects.filter(
            responses__is_internal=False,
        ).distinct().count()
        unresponded_count = total_feedback - responded_count

        # Add statistics to context
        context.update({
            'total_feedback': total_feedback,
            'responded_count': responded_count,
            'unresponded_count': unresponded_count,
            'section_title': 'All Feedback',
            'feedback_type_stats': Feedback.objects.values(
                'feedback_type'
            ).annotate(count=Count('id')),
            'status_stats': Feedback.objects.values(
                'status'
            ).annotate(count=Count('id')),
            'priority_stats': Feedback.objects.values(
                'priority'
            ).annotate(count=Count('id'))
        })
        return context

@staff_admin_required
@require_http_methods(["GET"])
def get_feedback_responses(request, feedback_id):
    try:
        feedback = Feedback.objects.get(id=feedback_id)
        responses = feedback.responses.all().order_by('-created_at')
        
        response_data = {
            'status': feedback.status,
            'responses': [{
                'response': response.response,
                'is_internal': response.is_internal,
                'created_at': response.created_at.isoformat(),
            } for response in responses]
        }
        
        return JsonResponse(response_data)
    except Feedback.DoesNotExist:
        return JsonResponse({'error': 'Feedback not found'}, status=404)

@staff_admin_required
@require_http_methods(["POST"])
def respond_to_feedback(request, feedback_id):
    try:
        feedback = Feedback.objects.get(id=feedback_id)
        data = json.loads(request.body)
        
        # Create new response
        FeedbackResponse.objects.create(
            feedback=feedback,
            responder=request.user,
            response=data['response'],
            is_internal=data['is_internal']
        )
        
        # Update feedback status if provided
        if 'status' in data:
            feedback.status = data['status']
            feedback.save()
        
        return JsonResponse({'status': 'success'})
    except Feedback.DoesNotExist:
        return JsonResponse({'error': 'Feedback not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    


class GoogleDriveService:
    def __init__(self):
        self.credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_DRIVE_SETTINGS['SERVICE_ACCOUNT_FILE'],
            scopes=settings.GOOGLE_DRIVE_SETTINGS['SCOPES']
        )
        self.service = build('drive', 'v3', credentials=self.credentials)

    def grant_access(self, file_id, email):
        try:
            permission = {
                'type': 'user',
                'role': 'reader',
                'emailAddress': email
            }
            result = self.service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=False
            ).execute()
            return result.get('id')
        except Exception as e:
            logger.error(f"Failed to grant access: {str(e)}")
            raise

    def revoke_access(self, file_id, permission_id):
        try:
            self.service.permissions().delete(
                fileId=file_id,
                permissionId=permission_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to revoke access: {str(e)}")
            raise



@login_required
def initiate_pesapal_payment(request, app_id):
    """Initiate PesaPal payment."""
    app = get_object_or_404(App, id=app_id)
    
    # Rate limiting
    cache_key = f"purchase_attempt_{request.user.id}"
    if cache.get(cache_key):
        return HttpResponseForbidden("Please wait before attempting another purchase")
    cache.set(cache_key, True, 60)  # 1 minute timeout

    try:
        # Create purchase record
        purchase = Purchase.objects.create(
            user=request.user,
            app=app,
            amount_paid=app.amount,
            currency=app.currency,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )

        # Get PesaPal redirect URL
        redirect_url = submit_pesapal_order_request(purchase)
        return redirect(redirect_url)
    except Exception as e:
        logger.error(f"PesaPal payment initiation failed: {str(e)}")
        return JsonResponse({'error': 'Payment initiation failed'}, status=500)


@login_required
def pesapal_callback(request):
    """Handle PesaPal callback after payment."""
    transaction_id = request.GET.get("OrderTrackingId")
    status = request.GET.get("OrderStatus")
    
    try:
        purchase = Purchase.objects.get(purchase_id=transaction_id)
        if status == "COMPLETED":
            purchase.mark_as_completed()
            # Create download token
            token = DownloadToken.objects.create(
                purchase=purchase,
                short_code=generate_short_code(),
                expiry_time=calculate_expiry_time(),
                user_ip=request.META.get('REMOTE_ADDR')
            )
            return redirect('apps:download_file', short_code=token.short_code)
        else:
            purchase.mark_as_failed()
            return JsonResponse({'error': 'Payment failed'}, status=400)
    except Exception as e:
        logger.error(f"PesaPal callback failed: {str(e)}")
        return JsonResponse({'error': 'Callback processing failed'}, status=500)

@login_required
def pesapal_ipn(request):
    """Handle PesaPal IPN (Instant Payment Notification)."""
    transaction_id = request.POST.get("OrderNotificationId")
    status = request.POST.get("OrderStatus")
    
    try:
        purchase = Purchase.objects.get(purchase_id=transaction_id)
        purchase.payment_status = status
        purchase.save()
        return JsonResponse({'status': 'success'}, status=200)
    except Exception as e:
        logger.error(f"PesaPal IPN failed: {str(e)}")
        return JsonResponse({'error': 'IPN processing failed'}, status=500)
    

@login_required
def purchase_app(request, app_id):
    """Handle app purchase using PesaPal."""
    app = get_object_or_404(App, id=app_id)
    
    # Rate limiting
    cache_key = f"purchase_attempt_{request.user.id}"
    if cache.get(cache_key):
        return HttpResponseForbidden("Please wait before attempting another purchase")
    cache.set(cache_key, True, 60)  # 1 minute timeout

    try:
        # Create purchase record
        purchase = Purchase.objects.create(
            user=request.user,
            app=app,
            amount_paid=app.amount,
            currency=app.currency,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )

        # Get PesaPal redirect URL
        redirect_url = submit_pesapal_order_request(purchase)
        if not redirect_url:
            logger.error("Failed to get PesaPal redirect URL")
            return JsonResponse({'error': 'Payment initiation failed'}, status=500)

        return redirect(redirect_url)  # Redirect to PesaPal payment page

    except Exception as e:
        logger.error(f"Purchase failed: {str(e)}")
        return JsonResponse({'error': 'Purchase failed'}, status=500)

@login_required
def download_file(request, short_code):
    token = get_object_or_404(DownloadToken, short_code=short_code)
    
    # Rate limiting for download attempts
    cache_key = f"download_attempt_{token.short_code}"
    if cache.get(cache_key, 0) >= 5:  # Max 5 attempts per minute
        return HttpResponseForbidden("Too many download attempts")
    cache.incr(cache_key, 1)
    cache.expire(cache_key, 60)  # 1 minute timeout

    try:
        if not token.can_download():
            raise PermissionDenied("Download token is invalid or expired")

        if not validate_ip_address(token, request):
            logger.warning(f"IP mismatch for token {token.short_code}")
            raise PermissionDenied("IP address mismatch")

        # Generate download URL
        drive_url = token.purchase.drive_file.generate_download_url(
            token.purchase.user.email
        )

        # Record download attempt
        token.record_download(
            request.META.get('REMOTE_ADDR'),
            request.META.get('HTTP_USER_AGENT')
        )

        return redirect(drive_url)

    except PermissionDenied as e:
        return HttpResponseForbidden(str(e))
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        return JsonResponse({'error': 'Download failed'}, status=500)

