import io
import time
import base64
import numpy as np
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg (non-interactive)
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import pandas as pd
import geopandas as gpd
from wordcloud import WordCloud

from django.shortcuts import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import (
    ListView,
    DetailView,
    TemplateView
)
from django.db.models import (
    Count,
    Sum,
    Avg,
    Q,
    F,
    Case,
    When,
    Value,
    FloatField,
    IntegerField
)
from django.db.models.functions import (
    Coalesce,
    Cast,
    TruncDay,
    TruncWeek,
    TruncMonth,
    TruncYear
)
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.core.cache import cache

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from apps.models import (
    App,
    AppViewHistory,
    AppDownloadHistory,
    SavedApp,
    AppFeedback,
    SearchQuery,
    AppReaction,
    LinkClick
  
)
from .permission import StaffAndAdminRequiredMixin,staff_admin_required
from users.models import CustomUser
from django.views.generic import DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import NotificationPost, NotificationInteraction

class AppDetailView(DetailView):
    model = NotificationPost
    template_name = 'ProAir/notification_popup.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.user.is_authenticated:
            NotificationInteraction.record_interaction(
                post=obj,
                user=self.request.user,
                interaction_type='clicked'
            )
        return obj

@require_POST
def close_notification(request):
    notification_id = request.POST.get('notification_id')
    if notification_id and request.user.is_authenticated:
        post = NotificationPost.objects.get(id=notification_id)
        NotificationInteraction.record_interaction(
            post=post,
            user=request.user,
            interaction_type='closed'
        )
    return JsonResponse({'status': 'success'})

class AdminOverviewView(LoginRequiredMixin,StaffAndAdminRequiredMixin,TemplateView):
    template_name ='ProAir/admin_overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Part 1: User Statistics
        context['user_count'] = CustomUser.objects.distinct().count()
        
        # Part 2: App Statistics
        apps = App.objects.aggregate(
            total_apps=Count('id', distinct=True),
            total_videos=Count('video', 
                             filter=Q(video__isnull=False), 
                             distinct=True),
            total_video_size=Sum('video_size', 
                               filter=Q(video__isnull=False),
                               distinct=True),
            total_youtube_links=Count('youtube_link', 
                                    filter=Q(youtube_link__isnull=False), 
                                    distinct=True),
            total_app_files=Count('app_file', 
                                filter=Q(app_file__isnull=False), 
                                distinct=True),
            total_banned=Count('id', 
                             filter=Q(banned=True), 
                             distinct=True),
            total_drive_links=Count('google_drive_link', 
                                  filter=Q(google_drive_link__isnull=False), 
                                  distinct=True)
        )
        context.update(apps)
        
        # Part 3: View History Statistics
        # Sum the actual view_count field instead of counting rows
        views = (
            AppViewHistory.objects
            .values('app_id')  # Group by app to avoid duplicates
            .distinct()  # Ensure uniqueness
            .aggregate(total_views=Sum('view_count'))  # Sum the distinct views
        )
        context.update(views)

        
        # Count distinct combinations of device type and app
        context['device_types'] = (
        AppViewHistory.objects
        .values('device_type')
        .annotate(count=Count('viewer_ip', distinct=True))  # Count distinct viewer IPs per device type
        .filter(device_type__isnull=False)
    )

        
        # Part 4: Download Statistics
        downloads = AppDownloadHistory.objects.aggregate(
            total_downloads=Count('id', distinct=True),
            total_download_size=Sum('file_size', distinct=True),
            total_download_count=Sum('download_count')  # Sum the actual download_count
        )
        context.update(downloads)
        
        context['download_formats'] = (
            AppDownloadHistory.objects
            .values('download_format')
            .annotate(count=Sum('download_count'))
            .filter(download_format__isnull=False)
        )
        
        # Part 5: Saved Apps Statistics
        context['total_saved'] = SavedApp.objects.distinct().count()
        
        # Part 6: Feedback Statistics
        feedback = AppFeedback.objects.aggregate(
            total_comments=Count('id', distinct=True),
            average_rating=Avg('rating')
        )
        context.update(feedback)
        
        context['rating_distribution'] = (
            AppFeedback.objects
            .values('rating')
            .annotate(count=Count('id', distinct=True))
            .order_by('rating')
        )
        
        # Part 7: Search Statistics
        searches = SearchQuery.objects.aggregate(
            total_searches=Count('id', distinct=True),
            unique_queries=Count('query', distinct=True),
            unique_results=Count('results_count', distinct=True)
        )
        context.update(searches)
        
        # Part 8: Reaction Statistics
        # Count distinct combinations of app and user for each reaction type
        reactions = (
            AppReaction.objects
            .values('reaction')
            .annotate(count=Count('id', distinct=True))
        )
        
        context['reactions'] = {
            'likes': next((r['count'] for r in reactions if r['reaction'] == 'like'), 0),
            'dislikes': next((r['count'] for r in reactions if r['reaction'] == 'dislike'), 0),
            'neutral': next((r['count'] for r in reactions if r['reaction'] == 'neutral'), 0)
        }
        
        # Part 9: Link Click Statistics
        # Count distinct combinations of app, user, and session for clicks
        clicks = LinkClick.objects.aggregate(
            total_clicks=Count('id', distinct=True),
            youtube_clicks=Count('id', 
                               filter=Q(link_type='youtube'), 
                               distinct=True),
            drive_clicks=Count('id', 
                             filter=Q(link_type='drive'), 
                             distinct=True)
        )
        context.update(clicks)
        
        return context


class AdminAppListView(LoginRequiredMixin,StaffAndAdminRequiredMixin,ListView):
    model = App
    template_name = 'ProAir/admin_app_list.html'
    context_object_name = 'apps'
    
    def get_queryset(self):
        # Annotate all required counts in a single query
        return App.objects.annotate(
            total_views=Coalesce(Count('appviewhistory', distinct=True), 0),
            total_downloads=Coalesce(Count('appdownloadhistory', distinct=True), 0),
            total_saves=Coalesce(Count('savedapp', distinct=True), 0),
            total_feedback=Coalesce(Count('appfeedback', distinct=True), 0),
            total_reactions=Coalesce(Count('appreaction', distinct=True), 0),
            total_link_clicks=Coalesce(Count('linkclick', distinct=True), 0),
            avg_rating=Coalesce(Avg('appfeedback__rating'), 0,output_field=FloatField()),
            search_count=Coalesce(
                Count(
                    'title',
                    filter=Q(title__in=SearchQuery.objects.values_list('query', flat=True)),
                    distinct=True
                ),
                0
            )
        ).select_related('author')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        for app in context['apps']:
            app.public_url = self.request.build_absolute_uri(
                reverse('apps:app_detail', kwargs={'pk': app.pk})
            )
        context['total_apps'] = self.get_queryset().count()
        return context
    

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({
                'status': 'error',
                'message': 'Permission denied'
            }, status=403)

        try:
            app_id = request.POST.get('app_id')
            action = request.POST.get('action')
            password = request.POST.get('password')
            
            app = App.objects.get(id=app_id)
            
            if action == 'ban':
                app.banned = True
                app.save()
                message = 'App successfully banned'
            elif action == 'unban':
                app.banned = False
                app.save()
                message = 'App successfully unbanned'
            elif action == 'delete':
                if request.user.check_password(password):
                    app.delete()
                    message = 'App successfully deleted'
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Invalid password'
                    }, status=403)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid action'
                }, status=400)
            
            return JsonResponse({
                'status': 'success',
                'message': message
            })
            
        except App.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'App not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class AppDetailView(LoginRequiredMixin,StaffAndAdminRequiredMixin,DetailView):
    model = App
    template_name ='ProAir/admin_app_detail.html.html'
    context_object_name = 'app'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app = self.object
        
        app_detail_url = self.request.build_absolute_uri(
            reverse('apps:app_detail', kwargs={'pk': self.object.pk})
        )
        context['app_detail_url'] = app_detail_url
        # App View History Analytics
        view_analytics = AppViewHistory.objects.filter(app=app).aggregate(
            total_views=Coalesce(Sum('view_count'), 0, output_field=IntegerField()),
            desktop_views=Coalesce(Sum('view_count', filter=Q(device_type='desktop')), 0, output_field=IntegerField()),
            mobile_views=Coalesce(Sum('view_count', filter=Q(device_type='mobile')), 0, output_field=IntegerField()),
            tablet_views=Coalesce(Sum('view_count', filter=Q(device_type='tablet')), 0, output_field=IntegerField()),
        )
        
        os_distribution = (AppViewHistory.objects.filter(app=app)
            .values('os')
            .annotate(
                count=Cast(Count('id'), output_field=IntegerField()),
                percentage=Cast(Count('id') * 100.0 / app.appviewhistory_set.count(), output_field=FloatField())
            )
            .order_by('-count'))
        
        # Download History Analytics
        download_analytics = AppDownloadHistory.objects.filter(app=app).aggregate(
            total_downloads=Coalesce(Sum('download_count'), 0, output_field=IntegerField()),
            desktop_downloads=Coalesce(Sum('download_count', filter=Q(device_type='desktop')), 0, output_field=IntegerField()),
            mobile_downloads=Coalesce(Sum('download_count', filter=Q(device_type='mobile')), 0, output_field=IntegerField()),
            tablet_downloads=Coalesce(Sum('download_count', filter=Q(device_type='tablet')), 0, output_field=IntegerField()),
            total_download_size=Coalesce(Sum('file_size'), 0.0, output_field=FloatField()),
        )
        
        download_formats = (AppDownloadHistory.objects.filter(app=app)
            .values('download_format')
            .annotate(
                count=Cast(Count('id'), output_field=IntegerField()),
                percentage=Cast(Count('id') * 100.0 / app.appdownloadhistory_set.count(), output_field=FloatField())
            )
            .order_by('-count'))
            
        download_os = (AppDownloadHistory.objects.filter(app=app)
            .values('os')
            .annotate(
                count=Cast(Count('id'), output_field=IntegerField()),
                percentage=Cast(Count('id') * 100.0 / app.appdownloadhistory_set.count(), output_field=FloatField())
            )
            .order_by('-count'))
        
        # Feedback Analytics
        feedback_analytics = AppFeedback.objects.filter(app=app).aggregate(
            total_feedback=Cast(Count('id'), output_field=IntegerField()),
            total_comments=Cast(Count('comment', filter=Q(comment__isnull=False)), output_field=IntegerField()),
            avg_rating=Coalesce(Avg('rating'), 0.0, output_field=FloatField()),
            approved_count=Cast(Count('id'), output_field=IntegerField())
        )
        
        rating_distribution = (AppFeedback.objects.filter(app=app)
            .values('rating')
            .annotate(
                count=Cast(Count('id'), output_field=IntegerField()),
                percentage=Cast(Count('id') * 100.0 / app.appfeedback_set.count(), output_field=FloatField())
            )
            .order_by('rating'))
        
        # Reaction Analytics
        reaction_analytics = AppReaction.objects.filter(app=app).aggregate(
            total_reactions=Cast(Count('id'), output_field=IntegerField()),
            likes=Cast(Count('id', filter=Q(reaction='like')), output_field=IntegerField()),
            dislikes=Cast(Count('id', filter=Q(reaction='dislike')), output_field=IntegerField()),
            neutral=Cast(Count('id', filter=Q(reaction='neutral')), output_field=IntegerField())
        )
        
        # Link Click Analytics
        link_analytics = LinkClick.objects.filter(app=app).aggregate(
            total_clicks=Cast(Count('id'), output_field=IntegerField()),
            youtube_clicks=Cast(Count('id', filter=Q(link_type='youtube')), output_field=IntegerField()),
            drive_clicks=Cast(Count('id', filter=Q(link_type='drive')), output_field=IntegerField())
        )
        
        context.update({
            'view_analytics': view_analytics,
            'os_distribution': os_distribution,
            'download_analytics': download_analytics,
            'download_formats': download_formats,
            'download_os': download_os,
            'feedback_analytics': feedback_analytics,
            'rating_distribution': rating_distribution,
            'reaction_analytics': reaction_analytics,
            'link_analytics': link_analytics,
        })
        
        return context

class AppApprovalView(LoginRequiredMixin,StaffAndAdminRequiredMixin, ListView):
    model = App
    template_name = 'ProAir/admin_approval.html'
    context_object_name = 'apps'
    
    def get_queryset(self):
        # Fetch only banned apps
        return App.objects.select_related('author').filter(
            banned=True
        ).order_by('-timestamp')
    
    def post(self, request, *args, **kwargs):
        try:
            app_id = request.POST.get('app_id')
            action = request.POST.get('action')
            password = request.POST.get('password')  # For delete action
            
            app = App.objects.get(id=app_id)
            
            if action == 'unban':
                app.banned = False
            elif action == 'delete':
                # Check if the user is an admin and the password is correct
                if request.user.is_staff and request.user.check_password(password):
                    app.delete()
                    return JsonResponse({
                        'status': 'success',
                        'message': 'App successfully deleted'
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Invalid password or insufficient permissions'
                    }, status=403)
            
            app.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'App successfully {action}ed'
            })
            
        except App.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'App not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class SearchAnalyticsView(LoginRequiredMixin,StaffAndAdminRequiredMixin, ListView):
    model = SearchQuery
    template_name = 'ProAir/admin_search_analytics.html'
    context_object_name = 'search_queries'
    paginate_by = 50

    def get_queryset(self):
        # Get search queries ordered by results count
        return SearchQuery.objects.select_related('user')\
            .order_by('-results_count', '-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # For each search query, get related apps that match the query
        for query in context['search_queries']:
            matching_apps = App.objects.filter(
                title__icontains=query.query,
                banned=False
            ).select_related('author')
            
            query.matching_apps = matching_apps
            
        return context
    



# YouTube API setup
API_KEY = 'AIzaSyCJFxvWMfN5JORXyZ5POrrJK7kevivapmQ'  # Replace with your API key
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)

from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.core.exceptions import RequestDataTooBig
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

@staff_admin_required
@cache_page(60 * 15)  # Cache for 15 minutes
def channel_info(request):
    try:
        channel_id = 'UCnInKH5C_4X3C2S8vcjItRA'
        
        # Request channel information
        channel_request = youtube.channels().list(
            part='snippet,statistics,brandingSettings,contentDetails',
            id=channel_id
        )
        response = channel_request.execute()
        
        # Get playlists count
        playlists_request = youtube.playlists().list(
            part='snippet',
            channelId=channel_id,
            maxResults=50
        )
        playlists_response = playlists_request.execute()
        total_playlists = len(playlists_response.get('items', []))
        
        # Get channel data with fallback to empty dict
        channel_data = response.get('items', [{}])[0]
        
        # Prepare context with relevant channel information
        context = {
            'channel_data': {
                'title': channel_data.get('snippet', {}).get('title'),
                'description': channel_data.get('snippet', {}).get('description'),
                'thumbnail': channel_data.get('snippet', {}).get('thumbnails', {}).get('default', {}).get('url'),
                'statistics': {
                    'subscribers': channel_data.get('statistics', {}).get('subscriberCount', '0'),
                    'views': channel_data.get('statistics', {}).get('viewCount', '0'),
                    'videos': channel_data.get('statistics', {}).get('videoCount', '0'),
                    'comments': channel_data.get('statistics', {}).get('commentCount', '0'),
                    'playlists': total_playlists
                },
                'published_at': channel_data.get('snippet', {}).get('publishedAt'),
                'custom_url': channel_data.get('snippet', {}).get('customUrl'),
                'country': channel_data.get('snippet', {}).get('country'),
                'banner': channel_data.get('brandingSettings', {}).get('image', {}).get('bannerExternalUrl')
            }
        }
        
        return render(request, 'ProAir/channel.html', context)
        
    except HttpError as e:
        error_message = f"YouTube API Error: {str(e)}"
        return render(request, 'ProAir/error.html', {'error': error_message})
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        return render(request, 'ProAir/error.html', {'error': error_message})
    
@staff_admin_required
@cache_page(60 * 15)  # Cache for 15 minutes
def video_list(request):
    try:
        channel_id = 'UCnInKH5C_4X3C2S8vcjItRA'
        videos = []
        next_page_token = None
        
        # Get channel statistics
        channel_request = youtube.channels().list(
            part='statistics',
            id=channel_id
        )
        channel_response = channel_request.execute()
        total_subscribers = channel_response['items'][0]['statistics']['subscriberCount']
        
        while True:
            # Get list of video IDs first
            search_request = youtube.search().list(
                part='snippet',
                channelId=channel_id,
                maxResults=50,
                type='video',
                pageToken=next_page_token
            )
            search_response = search_request.execute()
            
            # Extract video IDs
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            # Get detailed information for each video
            if video_ids:
                video_request = youtube.videos().list(
                    part='snippet,contentDetails,statistics,status',
                    id=','.join(video_ids)
                )
                video_response = video_request.execute()
                videos.extend(video_response.get('items', []))
            
            next_page_token = search_response.get('nextPageToken')
            if not next_page_token:
                break
                
        return render(request, 'ProAir/videos.html', {
            'videos': videos,
            'total_subscribers': total_subscribers
        })
    except Exception as e:
        return render(request, 'ProAir/videos.html', {'error': str(e)})
 
@staff_admin_required
@cache_page(60 * 15)  # Cache for 15 minutes
def playlist_list(request):
    try:
        channel_id = 'UCnInKH5C_4X3C2S8vcjItRA'
        playlist_request = youtube.playlists().list(
            part='snippet,contentDetails',  # Added contentDetails to get item count
            channelId=channel_id,
            maxResults=50
        )
        response = playlist_request.execute()
        playlists = response.get('items', [])
        
        # Get detailed information for each playlist including items
        enhanced_playlists = []
        for playlist in playlists:
            playlist_id = playlist['id']
            
            # Get playlist items
            playlist_items_request = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=playlist_id,
                maxResults=50
            )
            playlist_items_response = playlist_items_request.execute()
            
            # Get video IDs from playlist items
            video_ids = [item['contentDetails']['videoId'] 
                        for item in playlist_items_response.get('items', [])]
            
            # Get video statistics if there are videos
            video_details = []
            if video_ids:
                # Process video IDs in chunks of 50 (API limit)
                for i in range(0, len(video_ids), 50):
                    chunk = video_ids[i:i + 50]
                    videos_request = youtube.videos().list(
                        part='snippet,statistics',
                        id=','.join(chunk)
                    )
                    videos_response = videos_request.execute()
                    video_details.extend(videos_response.get('items', []))
            
            enhanced_playlist = {
                'id': playlist_id,
                'title': playlist['snippet']['title'],
                'description': playlist['snippet']['description'],
                'thumbnails': playlist['snippet']['thumbnails'],
                'itemCount': playlist['contentDetails']['itemCount'],
                'publishedAt': playlist['snippet']['publishedAt'],
                'videos': video_details
            }
            enhanced_playlists.append(enhanced_playlist)
            
        return render(request, 'ProAir/playlists.html', {
            'playlist_data': enhanced_playlists
        })
    except Exception as e:
        return render(request, 'ProAir/error.html', {'error': str(e)})


YOUTUBE_API_KEY = 'AIzaSyCJFxvWMfN5JORXyZ5POrrJK7kevivapmQ'  
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

@cache_page(60 * 60)  # Cache for 1 hour
def video_watch_hour(request):
    try:
        channel_id = 'UCnInKH5C_4X3C2S8vcjItRA'
        videos = []
        next_page_token = None

        # Check if data is already cached
        cache_key = f'youtube_videos_{channel_id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return render(request, 'ProAir/videos.html', cached_data)

        # Get channel statistics
        channel_request = youtube.channels().list(
            part='statistics',
            id=channel_id
        )
        channel_response = channel_request.execute()
        total_subscribers = channel_response['items'][0]['statistics']['subscriberCount']

        # Fetch videos with pagination and rate limiting
        while True:
            try:
                # Fetch video IDs
                search_request = youtube.search().list(
                    part='snippet',
                    channelId=channel_id,
                    maxResults=50,  # Fetch 50 videos per request
                    type='video',
                    pageToken=next_page_token
                )
                search_response = search_request.execute()

                # Extract video IDs
                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]

                # Fetch detailed video information
                if video_ids:
                    video_request = youtube.videos().list(
                        part='snippet,contentDetails,statistics,status',
                        id=','.join(video_ids)
                    )
                    video_response = video_request.execute()
                    videos.extend(video_response.get('items', []))

                # Check for more pages
                next_page_token = search_response.get('nextPageToken')
                if not next_page_token:
                    break

                # Rate limiting: Sleep for 1 second between requests
                time.sleep(1)

            except HttpError as e:
                # Handle API quota errors
                if e.resp.status == 403 and 'quotaExceeded' in str(e):
                    return render(request, 'ProAir/videos.html', {'error': 'API quota exceeded. Please try again later.'})
                else:
                    return render(request, 'ProAir/videos.html', {'error': str(e)})

        # Cache the results for 1 hour
        cache.set(cache_key, {
            'videos': videos,
            'total_subscribers': total_subscribers
        }, 60 * 60)

        return render(request, 'ProAir/videos.html', {
            'videos': videos,
            'total_subscribers': total_subscribers
        })

    except Exception as e:
        return render(request, 'ProAir/videos_watch_hour.html', {'error': str(e)})

@staff_admin_required   
def app_statistics(request):
    # Get period type and count from request parameters with defaults
    period_type = request.GET.get('period_type', 'week')
    period_count = int(request.GET.get('period_count', 12))
    
    # Get current date (timezone aware)
    now = timezone.now()
    
    # Set date range and truncation function based on period type
    if period_type == 'day':
        start_date = now - timedelta(days=period_count)
        trunc_function = TruncDay
        date_format = '%b %d'
        period_label = f'Last {period_count} Days'
    elif period_type == 'week':
        start_date = now - timedelta(weeks=period_count)
        trunc_function = TruncWeek
        date_format = '%b %d'
        period_label = f'Last {period_count} Weeks'
    elif period_type == 'month':
        start_date = now - timedelta(days=30*period_count)
        trunc_function = TruncMonth
        date_format = '%b %Y'
        period_label = f'Last {period_count} Months'
    else:  # year
        start_date = now - timedelta(days=365*period_count)
        trunc_function = TruncYear
        date_format = '%Y'
        period_label = f'Last {period_count} Years'
    
    # 1. Bar Chart: Number of apps created over time
    apps_over_time = (
        App.objects.filter(timestamp__gte=start_date)
        .annotate(period=trunc_function('timestamp'))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )
    
    # Prepare data for bar chart
    periods = [item['period'] for item in apps_over_time]
    counts = [item['count'] for item in apps_over_time]
    
    # Create bar chart
    fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
    ax_bar.bar(periods, counts, color='#4e73df')
    ax_bar.set_xlabel('Time Period')
    ax_bar.set_ylabel('Number of Apps')
    ax_bar.set_title(f'Number of Apps Created ({period_label})')
    
    # Format x-axis dates
    ax_bar.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_bar.savefig(buffer, format='png')
    buffer.seek(0)
    bar_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_bar)
    
    # 2. Pie Chart: Distribution of premium vs. free apps
    premium_distribution = (
        App.objects.annotate(
            app_type=Case(
                When(premium=True, then=1),
                default=0,
                output_field=IntegerField(),
            )
        )
        .values('app_type')
        .annotate(count=Count('id'))
        .order_by('app_type')
    )
    
    # Prepare data for pie chart
    labels = ['Free', 'Premium']
    sizes = [0, 0]  # Default values
    for item in premium_distribution:
        sizes[item['app_type']] = item['count']
    
    # Create pie chart
    fig_pie, ax_pie = plt.subplots(figsize=(8, 8))
    ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, 
               colors=['#36b9cc', '#1cc88a'], wedgeprops={'edgecolor': 'w'})
    ax_pie.set_title('Distribution of Apps: Free vs. Premium')
    ax_pie.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_pie.savefig(buffer, format='png')
    buffer.seek(0)
    pie_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_pie)
    
    # 3. Line Chart: Trend of app creation over time
    # We'll use the same data as the bar chart but with a line representation
    
    fig_line, ax_line = plt.subplots(figsize=(10, 5))
    ax_line.plot(periods, counts, marker='o', linestyle='-', color='#f6c23e')
    ax_line.set_xlabel('Time Period')
    ax_line.set_ylabel('Number of Apps')
    ax_line.set_title(f'Trend of App Creation Over Time ({period_label})')
    
    # Format x-axis dates
    ax_line.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_line.savefig(buffer, format='png')
    buffer.seek(0)
    line_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_line)
    
    # Get some additional statistics
    total_apps = App.objects.count()
    premium_apps = App.objects.filter(premium=True).count()
    free_apps = total_apps - premium_apps
    premium_percentage = (premium_apps / total_apps * 100) if total_apps > 0 else 0
    
    # Get apps created in the selected period for period stats
    apps_in_period = App.objects.filter(timestamp__gte=start_date).count()
    premium_in_period = App.objects.filter(timestamp__gte=start_date, premium=True).count()
    
    context = {
        'bar_chart': bar_chart,
        'pie_chart': pie_chart,
        'line_chart': line_chart,
        'period_type': period_type,
        'period_count': period_count,
        'period_label': period_label,
        'total_apps': total_apps,
        'premium_apps': premium_apps,
        'free_apps': free_apps,
        'premium_percentage': premium_percentage,
        'apps_in_period': apps_in_period,
        'premium_in_period': premium_in_period,
    }

    return render(request, 'ProAir/app_statistics.html', context)

@staff_admin_required
def app_view_statistics(request):
    # Get period type and count from request parameters with defaults
    period_type = request.GET.get('period_type', 'week')
    period_count = int(request.GET.get('period_count', 12))
    
    # Get current date (timezone aware)
    now = timezone.now()
    
    # Set date range and truncation function based on period type
    if period_type == 'day':
        start_date = now - timedelta(days=period_count)
        trunc_function = TruncDay
        date_format = '%b %d'
        period_label = f'Last {period_count} Days'
    elif period_type == 'week':
        start_date = now - timedelta(weeks=period_count)
        trunc_function = TruncWeek
        date_format = '%b %d'
        period_label = f'Last {period_count} Weeks'
    elif period_type == 'month':
        start_date = now - timedelta(days=30*period_count)
        trunc_function = TruncMonth
        date_format = '%b %Y'
        period_label = f'Last {period_count} Months'
    else:  # year
        start_date = now - timedelta(days=365*period_count)
        trunc_function = TruncYear
        date_format = '%Y'
        period_label = f'Last {period_count} Years'
    
    # 1. Bar Chart: Number of views over time
    views_over_time = (
        AppViewHistory.objects.filter(viewed_at__gte=start_date)
        .annotate(period=trunc_function('viewed_at'))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )
    
    # Prepare data for bar chart
    periods = [item['period'] for item in views_over_time]
    counts = [item['count'] for item in views_over_time]
    
    # Create bar chart
    fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
    ax_bar.bar(periods, counts, color='#4e73df')
    ax_bar.set_xlabel('Time Period')
    ax_bar.set_ylabel('Number of Views')
    ax_bar.set_title(f'Number of App Views ({period_label})')
    
    # Format x-axis dates
    ax_bar.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_bar.savefig(buffer, format='png')
    buffer.seek(0)
    bar_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_bar)
    
    # 2. Pie Chart: Distribution of views by device type
    device_distribution = (
        AppViewHistory.objects.values('device_type')
        .annotate(count=Count('id'))
        .order_by('device_type')
    )
    
    # Prepare data for pie chart
    labels = [item['device_type'] for item in device_distribution]
    sizes = [item['count'] for item in device_distribution]
    
    # Create pie chart
    fig_pie, ax_pie = plt.subplots(figsize=(8, 8))
    ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, 
               colors=['#36b9cc', '#1cc88a', '#f6c23e'], wedgeprops={'edgecolor': 'w'})
    ax_pie.set_title('Distribution of Views by Device Type')
    ax_pie.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_pie.savefig(buffer, format='png')
    buffer.seek(0)
    pie_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_pie)
    
    # 3. Line Chart: Trend of views over time
    fig_line, ax_line = plt.subplots(figsize=(10, 5))
    ax_line.plot(periods, counts, marker='o', linestyle='-', color='#f6c23e')
    ax_line.set_xlabel('Time Period')
    ax_line.set_ylabel('Number of Views')
    ax_line.set_title(f'Trend of App Views Over Time ({period_label})')
    
    # Format x-axis dates
    ax_line.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_line.savefig(buffer, format='png')
    buffer.seek(0)
    line_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_line)
    
    # Get some additional statistics
    total_views = AppViewHistory.objects.count()
    unique_users = AppViewHistory.objects.values('user').distinct().count()
    unique_ips = AppViewHistory.objects.values('viewer_ip').distinct().count()
    
    context = {
        'bar_chart': bar_chart,
        'pie_chart': pie_chart,
        'line_chart': line_chart,
        'period_type': period_type,
        'period_count': period_count,
        'period_label': period_label,
        'total_views': total_views,
        'unique_users': unique_users,
        'unique_ips': unique_ips,
    }

    return render(request, 'ProAir/app_view_statistics.html', context)

@staff_admin_required
def saved_app_statistics(request):
    # Get period type and count from request parameters with defaults
    period_type = request.GET.get('period_type', 'week')
    period_count = int(request.GET.get('period_count', 12))
    
    # Get current date (timezone aware)
    now = timezone.now()
    
    # Set date range and truncation function based on period type
    if period_type == 'day':
        start_date = now - timedelta(days=period_count)
        trunc_function = TruncDay
        date_format = '%b %d'
        period_label = f'Last {period_count} Days'
    elif period_type == 'week':
        start_date = now - timedelta(weeks=period_count)
        trunc_function = TruncWeek
        date_format = '%b %d'
        period_label = f'Last {period_count} Weeks'
    elif period_type == 'month':
        start_date = now - timedelta(days=30*period_count)
        trunc_function = TruncMonth
        date_format = '%b %Y'
        period_label = f'Last {period_count} Months'
    else:  # year
        start_date = now - timedelta(days=365*period_count)
        trunc_function = TruncYear
        date_format = '%Y'
        period_label = f'Last {period_count} Years'
    
    # 1. Bar Chart: Number of saves over time
    saves_over_time = (
        SavedApp.objects.filter(saved_at__gte=start_date)
        .annotate(period=trunc_function('saved_at'))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )
    
    # Prepare data for bar chart
    periods = [item['period'] for item in saves_over_time]
    counts = [item['count'] for item in saves_over_time]
    
    # Create bar chart
    fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
    ax_bar.bar(periods, counts, color='#4e73df')
    ax_bar.set_xlabel('Time Period')
    ax_bar.set_ylabel('Number of Saves')
    ax_bar.set_title(f'Number of App Saves ({period_label})')
    
    # Format x-axis dates
    ax_bar.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_bar.savefig(buffer, format='png')
    buffer.seek(0)
    bar_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_bar)
    
    # 2. Pie Chart: Distribution of saves by app
    app_save_distribution = (
        SavedApp.objects.values('app__title')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]  # Top 5 most saved apps
    )
    
    # Prepare data for pie chart
    labels = [item['app__title'] for item in app_save_distribution]
    sizes = [item['count'] for item in app_save_distribution]
    
    # Create pie chart
    fig_pie, ax_pie = plt.subplots(figsize=(8, 8))
    ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, 
               colors=['#36b9cc', '#1cc88a', '#f6c23e', '#e74a3b', '#858796'], wedgeprops={'edgecolor': 'w'})
    ax_pie.set_title('Top 5 Most Saved Apps')
    ax_pie.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_pie.savefig(buffer, format='png')
    buffer.seek(0)
    pie_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_pie)
    
    # 3. Line Chart: Trend of saves over time
    fig_line, ax_line = plt.subplots(figsize=(10, 5))
    ax_line.plot(periods, counts, marker='o', linestyle='-', color='#f6c23e')
    ax_line.set_xlabel('Time Period')
    ax_line.set_ylabel('Number of Saves')
    ax_line.set_title(f'Trend of App Saves Over Time ({period_label})')
    
    # Format x-axis dates
    ax_line.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_line.savefig(buffer, format='png')
    buffer.seek(0)
    line_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_line)
    
    # 4. Scatter Plot: Relationship between app views and saves
    app_views = (
        AppViewHistory.objects.values('app__title')
        .annotate(views=Count('id'))
        .order_by('-views')[:10]  # Top 10 most viewed apps
    )
    
    app_saves = (
        SavedApp.objects.values('app__title')
        .annotate(saves=Count('id'))
        .order_by('-saves')[:10]  # Top 10 most saved apps
    )
    
    # Merge views and saves data
    app_data = {}
    for item in app_views:
        app_data[item['app__title']] = {'views': item['views'], 'saves': 0}
    for item in app_saves:
        if item['app__title'] in app_data:
            app_data[item['app__title']]['saves'] = item['saves']
        else:
            app_data[item['app__title']] = {'views': 0, 'saves': item['saves']}
    
    # Prepare data for scatter plot
    app_titles = list(app_data.keys())
    views = [app_data[title]['views'] for title in app_titles]
    saves = [app_data[title]['saves'] for title in app_titles]
    
    # Create scatter plot
    fig_scatter, ax_scatter = plt.subplots(figsize=(10, 5))
    ax_scatter.scatter(views, saves, color='#4e73df')
    ax_scatter.set_xlabel('Number of Views')
    ax_scatter.set_ylabel('Number of Saves')
    ax_scatter.set_title('Relationship Between App Views and Saves')
    
    # Annotate points with app titles
    for i, title in enumerate(app_titles):
        ax_scatter.annotate(title, (views[i], saves[i]), fontsize=8, alpha=0.7)
    
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_scatter.savefig(buffer, format='png')
    buffer.seek(0)
    scatter_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_scatter)
    
    # Get some additional statistics
    total_saves = SavedApp.objects.count()
    unique_users_saving = SavedApp.objects.values('user').distinct().count()
    most_saved_app = app_save_distribution[0]['app__title'] if app_save_distribution else 'N/A'
    
    context = {
        'bar_chart': bar_chart,
        'pie_chart': pie_chart,
        'line_chart': line_chart,
        'scatter_chart': scatter_chart,
        'period_type': period_type,
        'period_count': period_count,
        'period_label': period_label,
        'total_saves': total_saves,
        'unique_users_saving': unique_users_saving,
        'most_saved_app': most_saved_app,
    }

    return render(request, 'ProAir/saved_app_statistics.html', context)

@staff_admin_required
def feedback_statistics(request):
    # Get period type and count from request parameters with defaults
    period_type = request.GET.get('period_type', 'week')
    period_count = int(request.GET.get('period_count', 12))
    
    # Get current date (timezone aware)
    now = timezone.now()
    
    # Set date range and truncation function based on period type
    if period_type == 'day':
        start_date = now - timedelta(days=period_count)
        trunc_function = TruncDay
        date_format = '%b %d'
        period_label = f'Last {period_count} Days'
    elif period_type == 'week':
        start_date = now - timedelta(weeks=period_count)
        trunc_function = TruncWeek
        date_format = '%b %d'
        period_label = f'Last {period_count} Weeks'
    elif period_type == 'month':
        start_date = now - timedelta(days=30*period_count)
        trunc_function = TruncMonth
        date_format = '%b %Y'
        period_label = f'Last {period_count} Months'
    else:  # year
        start_date = now - timedelta(days=365*period_count)
        trunc_function = TruncYear
        date_format = '%Y'
        period_label = f'Last {period_count} Years'
    
    # 1. Bar Chart: Distribution of ratings (1-star to 5-star)
    ratings_distribution = (
        AppFeedback.objects.filter(timestamp__gte=start_date)
        .values('rating')
        .annotate(count=Count('id'))
        .order_by('rating')
    )
    
    # Prepare data for bar chart
    ratings = [item['rating'] for item in ratings_distribution]
    counts = [item['count'] for item in ratings_distribution]
    
    # Create bar chart
    fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
    ax_bar.bar(ratings, counts, color='#4e73df')
    ax_bar.set_xlabel('Rating')
    ax_bar.set_ylabel('Number of Feedbacks')
    ax_bar.set_title(f'Distribution of Ratings ({period_label})')
    plt.xticks(ratings)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_bar.savefig(buffer, format='png')
    buffer.seek(0)
    bar_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_bar)
    
    # 2. Line Chart: Average rating of apps over time
    avg_ratings_over_time = (
        AppFeedback.objects.filter(timestamp__gte=start_date)
        .annotate(period=trunc_function('timestamp'))
        .values('period')
        .annotate(avg_rating=Avg('rating'))
        .order_by('period')
    )
    
    # Prepare data for line chart
    periods = [item['period'] for item in avg_ratings_over_time]
    avg_ratings = [item['avg_rating'] for item in avg_ratings_over_time]
    
    # Create line chart
    fig_line, ax_line = plt.subplots(figsize=(10, 5))
    ax_line.plot(periods, avg_ratings, marker='o', linestyle='-', color='#f6c23e')
    ax_line.set_xlabel('Time Period')
    ax_line.set_ylabel('Average Rating')
    ax_line.set_title(f'Average Rating Over Time ({period_label})')
    
    # Format x-axis dates
    ax_line.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_line.savefig(buffer, format='png')
    buffer.seek(0)
    line_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_line)
    
    # 3. Word Cloud: Most common words in comments
    comments = AppFeedback.objects.filter(timestamp__gte=start_date).values_list('comment', flat=True)
    text = ' '.join(comment for comment in comments if comment)
    
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    
    fig_wordcloud, ax_wordcloud = plt.subplots(figsize=(10, 5))
    ax_wordcloud.imshow(wordcloud, interpolation='bilinear')
    ax_wordcloud.axis('off')
    ax_wordcloud.set_title('Most Common Words in Comments')
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_wordcloud.savefig(buffer, format='png')
    buffer.seek(0)
    wordcloud_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_wordcloud)
    
    # 4. Stacked Bar Chart: Feedback approval status (is_approved vs. not approved)
    approval_distribution = (
        AppFeedback.objects.filter(timestamp__gte=start_date)
        .annotate(
            approval_status=Case(
                When(is_approved=True, then=1),
                default=0,
                output_field=IntegerField(),
            )
        )
        .values('approval_status')
        .annotate(count=Count('id'))
        .order_by('approval_status')
    )
    
    # Prepare data for stacked bar chart
    labels = ['Not Approved', 'Approved']
    sizes = [0, 0]  # Default values
    for item in approval_distribution:
        sizes[item['approval_status']] = item['count']
    
    # Create stacked bar chart
    fig_stacked, ax_stacked = plt.subplots(figsize=(10, 5))
    ax_stacked.bar(labels, sizes, color=['#e74a3b', '#1cc88a'])
    ax_stacked.set_xlabel('Approval Status')
    ax_stacked.set_ylabel('Number of Feedbacks')
    ax_stacked.set_title(f'Feedback Approval Status ({period_label})')
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_stacked.savefig(buffer, format='png')
    buffer.seek(0)
    stacked_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_stacked)
    
    # Get some additional statistics
    total_feedbacks = AppFeedback.objects.count()
    approved_feedbacks = AppFeedback.objects.filter(is_approved=True).count()
    not_approved_feedbacks = total_feedbacks - approved_feedbacks
    approval_percentage = (approved_feedbacks / total_feedbacks * 100) if total_feedbacks > 0 else 0
    
    # Get feedbacks created in the selected period for period stats
    feedbacks_in_period = AppFeedback.objects.filter(timestamp__gte=start_date).count()
    approved_in_period = AppFeedback.objects.filter(timestamp__gte=start_date, is_approved=True).count()
    
    context = {
        'bar_chart': bar_chart,
        'line_chart': line_chart,
        'wordcloud_chart': wordcloud_chart,
        'stacked_chart': stacked_chart,
        'period_type': period_type,
        'period_count': period_count,
        'period_label': period_label,
        'total_feedbacks': total_feedbacks,
        'approved_feedbacks': approved_feedbacks,
        'not_approved_feedbacks': not_approved_feedbacks,
        'approval_percentage': approval_percentage,
        'feedbacks_in_period': feedbacks_in_period,
        'approved_in_period': approved_in_period,
    }

    return render(request, 'ProAir/feedback_statistics.html', context)

@staff_admin_required
def reaction_statistics(request):
    # Get period type and count from request parameters with defaults
    period_type = request.GET.get('period_type', 'week')
    period_count = int(request.GET.get('period_count', 12))
    
    # Get current date (timezone aware)
    now = timezone.now()
    
    # Set date range and truncation function based on period type
    if period_type == 'day':
        start_date = now - timedelta(days=period_count)
        trunc_function = TruncDay
        date_format = '%b %d'
        period_label = f'Last {period_count} Days'
    elif period_type == 'week':
        start_date = now - timedelta(weeks=period_count)
        trunc_function = TruncWeek
        date_format = '%b %d'
        period_label = f'Last {period_count} Weeks'
    elif period_type == 'month':
        start_date = now - timedelta(days=30*period_count)
        trunc_function = TruncMonth
        date_format = '%b %Y'
        period_label = f'Last {period_count} Months'
    else:  # year
        start_date = now - timedelta(days=365*period_count)
        trunc_function = TruncYear
        date_format = '%Y'
        period_label = f'Last {period_count} Years'
    
    # 1. Line Chart: Trend of reactions over time
    reactions_over_time = (
        AppReaction.objects.filter(timestamp__gte=start_date)
        .annotate(period=trunc_function('timestamp'))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )
    
    # Prepare data for line chart
    periods = [item['period'] for item in reactions_over_time]
    counts = [item['count'] for item in reactions_over_time]
    
    # Create line chart
    fig_line, ax_line = plt.subplots(figsize=(10, 5))
    ax_line.plot(periods, counts, marker='o', linestyle='-', color='#f6c23e')
    ax_line.set_xlabel('Time Period')
    ax_line.set_ylabel('Number of Reactions')
    ax_line.set_title(f'Trend of Reactions Over Time ({period_label})')
    
    # Format x-axis dates
    ax_line.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_line.savefig(buffer, format='png')
    buffer.seek(0)
    line_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_line)
    
    # 2. Pie Chart: Distribution of reactions (like, dislike, neutral)
    reaction_distribution = (
        AppReaction.objects.annotate(
            reaction_type_code=Case(
                When(reaction_type='like', then=0),
                When(reaction_type='dislike', then=1),
                default=2,
                output_field=IntegerField(),
            )
        )
        .values('reaction_type_code')
        .annotate(count=Count('id'))
        .order_by('reaction_type_code')
    )
    
    # Prepare data for pie chart
    labels = ['Like', 'Dislike', 'Neutral']
    sizes = [0, 0, 0]  # Default values
    for item in reaction_distribution:
        sizes[item['reaction_type_code']] = item['count']
    
    # Create pie chart
    fig_pie, ax_pie = plt.subplots(figsize=(8, 8))
    ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, 
               colors=['#36b9cc', '#1cc88a', '#f6c23e'], wedgeprops={'edgecolor': 'w'})
    ax_pie.set_title('Distribution of Reactions')
    ax_pie.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_pie.savefig(buffer, format='png')
    buffer.seek(0)
    pie_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_pie)
    
    # 3. Bar Chart: Top 10 apps with the most likes
    top_liked_apps = (
        App.objects.annotate(like_count=Count('appreaction', filter=Q(appreaction__reaction_type='like')))
        .order_by('-like_count')[:10]
    )
    
    # Prepare data for bar chart
    app_names = [app.name for app in top_liked_apps]
    like_counts = [app.like_count for app in top_liked_apps]
    
    # Create bar chart
    fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
    ax_bar.bar(app_names, like_counts, color='#4e73df')
    ax_bar.set_xlabel('Apps')
    ax_bar.set_ylabel('Number of Likes')
    ax_bar.set_title('Top 10 Apps with the Most Likes')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_bar.savefig(buffer, format='png')
    buffer.seek(0)
    bar_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_bar)
    
    # Get some additional statistics
    total_reactions = AppReaction.objects.count()
    total_likes = AppReaction.objects.filter(reaction_type='like').count()
    total_dislikes = AppReaction.objects.filter(reaction_type='dislike').count()
    total_neutral = AppReaction.objects.filter(reaction_type='neutral').count()
    
    context = {
        'line_chart': line_chart,
        'pie_chart': pie_chart,
        'bar_chart': bar_chart,
        'period_type': period_type,
        'period_count': period_count,
        'period_label': period_label,
        'total_reactions': total_reactions,
        'total_likes': total_likes,
        'total_dislikes': total_dislikes,
        'total_neutral': total_neutral,
    }

    return render(request, 'ProAir/reaction_statistics.html', context)

@staff_admin_required
def link_click_statistics(request):
    # Get period type and count from request parameters with defaults
    period_type = request.GET.get('period_type', 'week')
    period_count = int(request.GET.get('period_count', 12))
    
    # Get current date (timezone aware)
    now = timezone.now()
    
    # Set date range and truncation function based on period type
    if period_type == 'day':
        start_date = now - timedelta(days=period_count)
        trunc_function = TruncDay
        date_format = '%b %d'
        period_label = f'Last {period_count} Days'
    elif period_type == 'week':
        start_date = now - timedelta(weeks=period_count)
        trunc_function = TruncWeek
        date_format = '%b %d'
        period_label = f'Last {period_count} Weeks'
    elif period_type == 'month':
        start_date = now - timedelta(days=30*period_count)
        trunc_function = TruncMonth
        date_format = '%b %Y'
        period_label = f'Last {period_count} Months'
    else:  # year
        start_date = now - timedelta(days=365*period_count)
        trunc_function = TruncYear
        date_format = '%Y'
        period_label = f'Last {period_count} Years'
    
    # 1. Bar Chart: Number of clicks by link type
    clicks_by_type = (
        LinkClick.objects.filter(clicked_at__gte=start_date)
        .values('link_type')
        .annotate(count=Count('id'))
        .order_by('link_type')
    )
    
    # Prepare data for bar chart
    link_types = [item['link_type'] for item in clicks_by_type]
    counts = [item['count'] for item in clicks_by_type]
    
    # Create bar chart
    fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
    ax_bar.bar(link_types, counts, color='#4e73df')
    ax_bar.set_xlabel('Link Type')
    ax_bar.set_ylabel('Number of Clicks')
    ax_bar.set_title(f'Number of Clicks by Link Type ({period_label})')
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_bar.savefig(buffer, format='png')
    buffer.seek(0)
    bar_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_bar)
    
    # 2. Line Chart: Click trends over time
    clicks_over_time = (
        LinkClick.objects.filter(clicked_at__gte=start_date)
        .annotate(period=trunc_function('clicked_at'))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )
    
    # Prepare data for line chart
    periods = [item['period'] for item in clicks_over_time]
    counts = [item['count'] for item in clicks_over_time]
    
    # Create line chart
    fig_line, ax_line = plt.subplots(figsize=(10, 5))
    ax_line.plot(periods, counts, marker='o', linestyle='-', color='#f6c23e')
    ax_line.set_xlabel('Time Period')
    ax_line.set_ylabel('Number of Clicks')
    ax_line.set_title(f'Click Trends Over Time ({period_label})')
    
    # Format x-axis dates
    ax_line.xaxis.set_major_formatter(DateFormatter(date_format))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_line.savefig(buffer, format='png')
    buffer.seek(0)
    line_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_line)
    
    # 3. Geographical Map: Show clicks by ip_address location
    # Get clicks by IP address
    clicks_by_ip = (
        LinkClick.objects.filter(clicked_at__gte=start_date)
        .values('ip_address')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]  # Top 10 IPs
    )
    
    # Convert IP addresses to locations (requires a geolocation API or library)
    # For simplicity, we'll use a placeholder for latitude and longitude
    locations = []
    for item in clicks_by_ip:
        ip = item['ip_address']
        count = item['count']
        # Replace with actual geolocation logic
        locations.append({'ip': ip, 'count': count, 'lat': 0, 'lon': 0})
    
    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(locations, geometry=gpd.points_from_xy([loc['lon'] for loc in locations], [loc['lat'] for loc in locations]))
    
    # Plot the map
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    fig_map, ax_map = plt.subplots(figsize=(10, 5))
    world.plot(ax=ax_map, color='lightgray')
    gdf.plot(ax=ax_map, marker='o', color='red', markersize=gdf['count'] * 10, alpha=0.6)
    ax_map.set_title('Clicks by IP Address Location')
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = io.BytesIO()
    fig_map.savefig(buffer, format='png')
    buffer.seek(0)
    map_chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig_map)
    
    # Get some additional statistics
    total_clicks = LinkClick.objects.count()
    unique_ips = LinkClick.objects.values('ip_address').distinct().count()
    unique_users = LinkClick.objects.values('user').distinct().count()
    
    context = {
        'bar_chart': bar_chart,
        'line_chart': line_chart,
        'map_chart': map_chart,
        'period_type': period_type,
        'period_count': period_count,
        'period_label': period_label,
        'total_clicks': total_clicks,
        'unique_ips': unique_ips,
        'unique_users': unique_users,
    }

    return render(request, 'ProAir/link_click_statistics.html', context)