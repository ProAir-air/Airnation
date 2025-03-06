from django.urls import path
from . import views

app_name = 'apps'

urlpatterns = [
    path('', views.AppListView.as_view(), name='app_list'),
    path('<int:pk>/', views.AppDetailView.as_view(), name='app_detail'),
    path('<int:pk>/download/', views.download_app, name='download_app'),
    path('<int:pk>/toggle-save/', views.toggle_save_app, name='toggle_save_app'),
    path('saved/', views.SavedAppListView.as_view(), name='saved_apps'),
    path('saved/delete/<int:id>/', views.delete_saved_app, name='delete_saved_app'),
    path('download-history/', views.download_history, name='download_history'),
    path('upload/', views.AppUploadView.as_view(), name='app_upload'),
    path('preview/<int:pk>/', views.AppPreviewView.as_view(), name='preview_app'),
    path('track-link-click/', views.track_link_click, name='track_link_click'),
    path('handle-reaction/', views.handle_reaction, name='handle_reaction'),
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('remove-download-history/<int:history_id>/', views.remove_download_history, name='remove_download_history'),
    path('app/<int:pk>/edit/', views.AppUpdateView.as_view(), name='app_edit'),
    path('app/<int:pk>/delete/', views.AppDeleteView.as_view(), name='app_delete'),
    path('my-apps/', views.UserAppsListView.as_view(), name='user_apps_list'),

    path("pay/<int:app_id>/", views.purchase_app, name="purchase_app"),
    path("pay/<int:app_id>/", views.initiate_pesapal_payment, name="initiate_pesapal_payment"),
    path("payment/callback/", views.pesapal_callback, name="pesapal_callback"),
    path("payment/ipn/", views.pesapal_ipn, name="pesapal_ipn"),

    path('download/<str:short_code>/', views.download_file, name='download_file'),


    path('create/', views.FeedbackCreateView.as_view(), name='feedback_create'),
    path('list/', views.FeedbackListView.as_view(), name='feedback_list'),
    path('detail/<int:pk>/', views.FeedbackDetailView.as_view(), name='feedback_detail'),
    path('update/<int:pk>/', views.FeedbackUpdateView.as_view(), name='feedback_update'),
    path('detail/<int:pk>/respond/', views.FeedbackResponseCreateView.as_view(), name='feedback_respond'),


    path('submit-request/', views.ApplicationRequestCreateView.as_view(), name='submit_request'),
    path("my-requests/", views.UserRequestsView.as_view(), name="user_requests"),
    path("admin/respond/<int:request_id>/", views.AdminRespondView.as_view(), name="admin_respond"),
    path('admin/unresponded/',views.UnrespondedRequestsView.as_view(), name='unresponded_requests'),
    
    path('admin/responded/', views.RespondedRequestsView.as_view(), name='responded_requests'),
    
    path('admin/all-requests/', views.AllRequestsOverviewView.as_view(), name='all_requests'),



    path('not', views.NotificationListView.as_view(), name='notification_list'),
    path('not/<int:pk>/', views.NotificationDetailView.as_view(), name='notification_detail'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('mark-read/', views.mark_notifications_read, name='mark_notifications_read'),

    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('unsent-notifications/', views.UnsentNotificationListView.as_view(), name='unsent_notifications'),
    path('update-notification-status/', views.UpdateNotificationStatusView.as_view(), name='update_notification_status'),
    path('sent-notifications/', views.SentNotificationsView.as_view(), name='sent_notifications'),

    path('feedback/unresponded/',views.UnrespondedFeedbackView.as_view(),name='unresponded_feedback'),
    path('feedback/responded/',views.RespondedFeedbackView.as_view(),name='responded_feedback'),
    path('feedback/all/',views. AllFeedbackView.as_view(), name='all_feedback'),

    path('feedback/<int:feedback_id>/responses/',views.get_feedback_responses,name='feedback_responses'),
    path('feedback/<int:feedback_id>/respond/',views.respond_to_feedback,name='respond_to_feedback'),




]