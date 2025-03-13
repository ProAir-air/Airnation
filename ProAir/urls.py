from django.urls import path
from . import views

app_name='ProAir'


urlpatterns = [
    path('admin/overview/', views.AdminOverviewView.as_view(), name='admin_overview'),
    path('app/<int:pk>/', views.AppDetailView.as_view(), name='app_detail'),
    path('admin/apps/', views.AdminAppListView.as_view(), name='admin_app_list'),
    path('admin/apps/approval/', views.AppApprovalView.as_view(), name='app_approval'),
    path('admin/search-analytics/', views.SearchAnalyticsView.as_view(), name='search_analytics'),


    path('channel/', views.channel_info, name='channel_info'),
    path('videos/', views.video_list, name='video_list'), 
    path('playlists/', views.playlist_list, name='playlist_list'),
    path('video_watch_hour/', views.video_watch_hour, name='video_watch_hour'),


    path('app-statistics/', views.app_statistics, name='app_statistics'),
    path('app-view-statistics/', views.app_view_statistics, name='app_view_statistics'),
    path('saved-app-statistics/', views.saved_app_statistics, name='saved_app_statistics'),
    path('feedback-statistics/', views.feedback_statistics, name='feedback_statistics'),
    path('reaction-statistics/', views.reaction_statistics, name='reaction_statistics'),
     path('link-click-statistics/', views.link_click_statistics, name='link_click_statistics'),



    
]

