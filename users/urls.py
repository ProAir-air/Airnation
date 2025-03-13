from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns=[
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),   
    path('verify/',views.verify_email, name='verify'),
    path('tos/', views.terms_of_use, name='terms_of_use'),
    path('privacy_policy/', views.privacy_policy, name='privacy_policy'),
    path('help_center/', views.help_center, name='help_center'),
    path('about/', views.about, name='about'),
    path('create/', views.create_profile, name='create_profile'),
    path('update/', views.update_profile, name='update_profile'),
    path('profile/<str:username>/', views.view_profile, name='view_profile'),

    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='users/password-reset.html'), name='password-reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='users/password-reset-done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='users/password-reset-confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='users/password-reset-complete.html'), name='password_reset_complete'),


    path('all-users/', views.user_list_view, name='user_list'),
    path('users/<int:user_or_session_id>/', views.user_activity_view, name='user_activity_view'),
    path('analytics/one-day/', views.OneDayAnalyticsView.as_view(), name='one_day_analytics'),
    path('analytics/two-days/',views.TwoDayAnalyticsView.as_view(), name='two_day_analytics'),
    path('analytics/three-days/', views.ThreeDayAnalyticsView.as_view(), name='three_day_analytics'),
    path('analytics/four-days/', views.FourDayAnalyticsView.as_view(), name='four_day_analytics'),
    path('analytics/six-days/', views.SixDayAnalyticsView.as_view(), name='six_day_analytics'),
    path('analytics/five-days/', views.FiveDayAnalyticsView.as_view(), name='five_day_analytics'),
    path('analytics/one-week/', views.OneWeekAnalyticsView.as_view(), name='one_week_analytics'),
    path('analytics/two-weeks/', views.TwoWeekAnalyticsView.as_view(), name='two_week_analytics'),
    path('analytics/one-month/', views.OneMonthAnalyticsView.as_view(), name='one_month_analytics'),
    path('analytics/two-months/', views.TwoMonthAnalyticsView.as_view(), name='two_month_analytics'),
    path('analytics/three-weeks/', views.ThreeWeekAnalyticsView.as_view(), name='three_week_analytics'),
    path('analytics/three-months/', views.ThreeMonthAnalyticsView.as_view(), name='three_month_analytics'),
    path('analytics/four-months/', views.FourMonthAnalyticsView.as_view(), name='four_month_analytics'),
    path('analytics/five-months/', views.FiveMonthAnalyticsView.as_view(), name='five_month_analytics'),
    path('analytics/six-months/', views.SixMonthAnalyticsView.as_view(), name='six_month_analytics'),
    path('analytics/seven-months/', views.SevenMonthAnalyticsView.as_view(), name='seven_month_analytics'),
    path('analytics/eight-months/', views.EightMonthAnalyticsView.as_view(), name='eight_month_analytics'),
    path('analytics/nine-months/', views.NineMonthAnalyticsView.as_view(), name='nine_month_analytics'),
    path('analytics/ten-months/', views.TenMonthAnalyticsView.as_view(), name='ten_month_analytics'),
    path('analytics/eleven-months/', views.ElevenMonthAnalyticsView.as_view(), name='eleven_month_analytics'),
    path('analytics/one-year/', views.OneYearAnalyticsView.as_view(), name='one_year_analytics'),





]