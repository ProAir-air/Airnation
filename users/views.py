import os
import re
import json
import random
import logging
import requests
from collections import defaultdict
from datetime import timedelta
from PIL import Image, UnidentifiedImageError

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import (
    CreateView,
    ListView,
    DetailView,
    DeleteView,
    UpdateView,
    TemplateView
)
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.core.exceptions import ValidationError
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.timezone import now, timedelta
from django.db import IntegrityError
from django.db.models import (
    Count,
    Sum,
    Min,
    Max,
    Avg,
    F,
    Q,
    OuterRef,
    Subquery
)
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import JsonResponse

from user_agents import parse


from .models import (
    CustomUser,
    Profile,
    UserActivity,
    PageVisit,
    DailyReport
)
from .forms import CustomUserCreationForm, ProfileForm
from apps.models import App, SavedApp, AppViewHistory
from ProAir.permission import StaffAndAdminRequiredMixin,staff_admin_required

class RegisterView(View):
    def get(self, request):
        form=CustomUserCreationForm
        return render(request, 'users/register.html', {'form':form})
    
    def post(self, request):
        form=CustomUserCreationForm(request.POST)
        if form.is_valid():
            user_data={
                'email':form.cleaned_data['email'],
                'username':form.cleaned_data['username'],
                'password':form.cleaned_data['password1'],
                
            }
            #store user data in session for later use
            request.session['user_data']=user_data
            #Generate verification code
            verification_code=''.join([str(random.randint(0,9)) for _ in range(6)])
            request.session['verification_code']=verification_code

            #send verfication code via email
            send_vefication_email(user_data['email'], verification_code)
            return redirect('verify')
        return render(request, self.template_name, {'form':form})


def send_vefication_email(email, verification_code):
    subject='Email Verification Code'
    message=f'''
    Thanks you for registering!
    Your verification code is:{verification_code}

    Please enter this code on the verification page to complete your registration
    '''
    try:
        send_mail(subject, message,settings.EMAIL_HOST_USER,
                  [email], fail_silently=False)

    except Exception as e:
        print(f'failed to send email: {str(e)}')    



def verify_email(request):
    if request.method == "POST":
        if 'resend_code' in request.POST:
            verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            request.session['verification_code'] = verification_code

            send_vefication_email(request.session['user_data']['email'], verification_code)
            return render(request, 'users/verify.html', {'message': 'A new verification code sent to your email'})

        entered_code = ''.join([
            request.POST.get(f'digit{i}', '') for i in range(1, 7)
        ])
        stored_code = request.session.get('verification_code')
        user_data = request.session.get('user_data')

        if entered_code == stored_code and user_data:
            try:
                # Check if email already exists
                if CustomUser.objects.filter(email=user_data['email']).exists():
                    return render(request, 'users/verify.html', 
                                {'error': 'Email already registered'})

                # Detect IP address
                ip_address = request.META.get('REMOTE_ADDR', None)

                # Fetch location using ipstack
                location_data = {}
                if ip_address:
                    try:
                        response = requests.get(
                            f"http://api.ipstack.com/{ip_address}?access_key=2066aa1BQZKqdp2CV3QV5nUEsqSg1ygegLmqRygj"
                        )
                        if response.status_code == 200:
                            location_data = response.json()
                    except Exception as e:
                        print(f"Error fetching location data: {e}")

                # Detect device
                user_agent = request.META.get('HTTP_USER_AGENT', "")
                parsed_agent = parse(user_agent)
                device = {
                    "browser": parsed_agent.browser.family,
                    "os": parsed_agent.os.family,
                    "device_type": (
                        "Mobile" if parsed_agent.is_mobile else
                        "Tablet" if parsed_agent.is_tablet else
                        "Desktop" if parsed_agent.is_pc else
                        "Smart TV" if parsed_agent.is_smarttv else
                        "Console" if parsed_agent.is_console else
                        "Wearable" if parsed_agent.is_wearable else
                        "IoT" if parsed_agent.is_iot else
                        "Unknown"
                    ),
                }

                # Create user with location and device data
                user = CustomUser.objects.create_user(
                    email=user_data['email'],
                    username=user_data['username'],
                    password=user_data['password'],
                )
                user.ip_address = ip_address
                user.country = location_data.get("country_name", "")
                user.city_or_region = location_data.get("city", "")
                user.district = location_data.get("region_name", "")
                user.continent = location_data.get("continent_name", "")

                # Update devices_used
                devices = user.devices_used if user.devices_used else []
                if device not in devices:  # Avoid duplicates
                    devices.append(device)
                user.devices_used = devices

                # Save the user instance
                user.save()

                # Clean up session
                del request.session['user_data']
                del request.session['verification_code']

                # Log in the user
                login(request, user)
                
                # Send donation email
                send_donation_email(user.email)
                
                # Redirect to create profile instead of apps:app_list
                return redirect('create_profile')

            except IntegrityError as e:
                return render(request, 'users/verify.html', 
                            {'error': 'Registration failed. Please try again.'})
        else:
            return render(request, 'users/verify.html', 
                        {'error': 'Invalid verification code'})

    return render(request, 'users/verify.html')

def send_donation_email(email):
    subject = 'Support Our Community'
    html_content = render_to_string('users/donation_email.html', {})

    email_message=EmailMultiAlternatives(
        subject=subject,
        body='Thank you for joining us',
        from_email=settings.EMAIL_HOST_USER,
        to=[email]
    )
    email_message.attach_alternative(html_content, 'text/html')

    try:
        email_message.send(fail_silently=False)
    except Exception as e:
        print(f'Failed to send email: :{str(e)}')    

class CustomLoginView(LoginView):
    template_name='users/login.html'
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid email or password. Please try again.')
        return super().form_invalid(form)

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValidationError as e:
            for error in e.messages:
                messages.error(self.request, error)
            return self.form_invalid(form)

class CustomLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.add_message(request, messages.INFO,"You must log in again because you logged out.")
        return redirect(reverse_lazy('login'))

@login_required
def create_profile(request):
    try:
        # Check if profile exists
        profile = request.user.profile
        return redirect('view_profile', username=request.user.username)
    except Profile.DoesNotExist:
        if request.method == 'POST':
            form = ProfileForm(request.POST, request.FILES)
            if form.is_valid():
                profile = form.save(commit=False)
                profile.user = request.user
                profile.save()
                messages.success(request, 'Profile created successfully!')
                return redirect('view_profile', username=request.user.username)
        else:
            form = ProfileForm()
        return render(request, 'users/create_profile.html', {'form': form})


@login_required
def update_profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('view_profile', username=request.user.username)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'users/update_profile.html', {
        'form': form,
        'profile': profile
    })


@login_required
def view_profile(request, username):
    # Get basic profile information
    user_profile = get_object_or_404(Profile, user__username=username)
    
    # Get saved apps
    saved_apps = SavedApp.objects.filter(user=user_profile.user).select_related('app')
    
    # Get top 5 viewed apps
    top_apps = App.objects.annotate(
        total_views=Count('appviewhistory__view_count')
    ).order_by('-total_views')[:5]
    
    context = {
        'profile': user_profile,
        'saved_apps': saved_apps,
        'top_apps': top_apps,
        'is_owner': request.user == user_profile.user if request.user.is_authenticated else False
    }
    
    return render(request, 'users/view_profile.html', context)

@staff_admin_required
@login_required
def user_list_view(request):
    # Summary Statistics
    total_users = CustomUser.objects.count()
    total_anonymous = UserActivity.objects.filter(user__isnull=True).count()
    
    total_visits = PageVisit.objects.count()
    total_time_spent = PageVisit.objects.aggregate(total_time=Sum('duration'))['total_time'] or 0
    avg_time_per_visit = PageVisit.objects.aggregate(avg_time=Avg('duration'))['avg_time'] or 0
    unique_pages_visited = PageVisit.objects.values('page_url').distinct().count()
    
    longest_page_duration = PageVisit.objects.aggregate(longest=Max('duration'))['longest'] or 0
    shortest_page_duration = PageVisit.objects.aggregate(shortest=Min('duration'))['shortest'] or 0
    
    most_visited_page = PageVisit.objects.values('page_url').annotate(count=Count('page_url')).order_by('-count').first()
    most_visited_page = most_visited_page['page_url'] if most_visited_page else 'N/A'

    # Authenticated Users Details
    authenticated_users = CustomUser.objects.annotate(
        total_visits=Count('useractivity__pagevisit', distinct=True),
        last_active=Max('useractivity__last_activity'),
        first_visit=Min('useractivity__start_time'),
        total_time_spent=Sum('useractivity__pagevisit__duration'),
        avg_time_per_visit=Avg('useractivity__pagevisit__duration'),
        unique_pages_visited=Count('useractivity__pagevisit__page_url', distinct=True),
        total_sessions=Count('useractivity', distinct=True),
        longest_page_duration=Max('useractivity__pagevisit__duration'),
        shortest_page_duration=Min('useractivity__pagevisit__duration'),
    ).order_by('-last_active')

    # Anonymous Users Details
    anonymous_sessions = UserActivity.objects.filter(
        user__isnull=True
    ).annotate(
        total_visits=Count('pagevisit'),
        total_time_spent=Sum('pagevisit__duration'),
        avg_time_per_visit=Avg('pagevisit__duration'),
        unique_pages_visited=Count('pagevisit__page_url', distinct=True),
        last_active=Max('last_activity'),
        first_visit=Min('start_time')
    ).order_by('-last_activity')

    context = {
        'summary': {
            'total_users': total_users,
            'total_anonymous': total_anonymous,
            'total_visits': total_visits,
            'total_time_spent': total_time_spent,
            'avg_time_per_visit': avg_time_per_visit,
            'unique_pages_visited': unique_pages_visited,
            'longest_page_duration': longest_page_duration,
            'shortest_page_duration': shortest_page_duration,
            'most_visited_page': most_visited_page,
        },
        'authenticated_users': authenticated_users,
        'anonymous_sessions': anonymous_sessions,
    }
    return render(request, 'users/tracking/user_list.html', context)
   
@staff_admin_required
@login_required
def user_activity_view(request, user_or_session_id):
    try:
        # Check if the ID corresponds to an authenticated user
        user = CustomUser.objects.get(id=user_or_session_id)
        page_visits = PageVisit.objects.filter(
            activity__user=user
        ).order_by('timestamp')
        username_or_session = user.username
        email = user.email
    except CustomUser.DoesNotExist:
        # If not found, treat the ID as an anonymous session
        session = get_object_or_404(UserActivity, id=user_or_session_id)
        page_visits = PageVisit.objects.filter(
            activity=session
        ).order_by('timestamp')
        username_or_session = f"Anonymous (Session: {session.session_id})"
        email = None

    # Aggregate overall information
    total_pages_visited = page_visits.count()
    total_time_spent = page_visits.aggregate(total_time=Sum('duration'))['total_time'] or 0
    first_visit = page_visits.aggregate(first_visit=Min('timestamp'))['first_visit']
    last_visit = page_visits.aggregate(last_visit=Max('timestamp'))['last_visit']

    # Top 5 most visited pages
    most_visited_pages = page_visits.values('page_url').annotate(
        count=Count('id'),
        total_time=Sum('duration'),
        first_visit=Min('timestamp'),
        last_visit=Max('timestamp')
    ).order_by('-count')[:5]

    # Top 5 least visited pages
    least_visited_pages = page_visits.values('page_url').annotate(
        count=Count('id'),
        total_time=Sum('duration'),
        first_visit=Min('timestamp'),
        last_visit=Max('timestamp')
    ).order_by('count')[:5]

    # Group page visits by date
    date_categorized_visits = defaultdict(list)
    for visit in page_visits:
        visit_date = visit.timestamp.date()
        date_categorized_visits[visit_date].append({
            'page_url': visit.page_url,
            'duration': visit.duration,
            'timestamp': visit.timestamp,
            'method': visit.method,
            'status_code': visit.status_code,
            'user_agent': visit.user_agent,
            'ip_address': visit.ip_address,
        })

    # Prepare context
    context = {
        'username_or_session': username_or_session,
        'email': email,
        'total_pages_visited': total_pages_visited,
        'total_time_spent': total_time_spent,
        'first_visit': first_visit,
        'last_visit': last_visit,
        'most_visited_pages': most_visited_pages,
        'least_visited_pages': least_visited_pages,
        'date_categorized_visits': dict(date_categorized_visits),
    }

    return render(request, 'users/tracking/user_analytics.html', context)


class BaseAnalyticsView(LoginRequiredMixin, StaffAndAdminRequiredMixin,TemplateView):
    """
    Base class for generating analytics reports for various time periods.
    """
    template_name = None
    period_hours = None
    title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        end_time = now()
        start_time = end_time - timedelta(hours=self.period_hours)

        # Calculate user statistics
        total_authenticated_users = UserActivity.objects.filter(
            start_time__range=(start_time, end_time), user__isnull=False
        ).values('user').distinct().count()

        total_anonymous_users = UserActivity.objects.filter(
            start_time__range=(start_time, end_time), user__isnull=True
        ).count()

        total_users = total_authenticated_users + total_anonymous_users

        # Calculate page statistics
        page_visits = PageVisit.objects.filter(timestamp__range=(start_time, end_time))
        total_pages_visited = page_visits.count()
        total_unique_pages = page_visits.values('page_url').distinct().count()

        # Calculate total time spent and page durations
        page_durations = page_visits.values('page_url').annotate(
            total_time=Sum('duration'),
            visit_count=Count('id'),
            first_visit=Min('timestamp'),
            last_visit=Max('timestamp')
        )

        # Prepare most and least visited pages
        most_visited_pages = page_durations.order_by('-visit_count')[:5]
        least_visited_pages = page_durations.order_by('visit_count')[:5]

        # Group page visits by date
        date_categorized_visits = defaultdict(list)
        for visit in page_visits:
            visit_date = visit.timestamp.date()
            date_categorized_visits[visit_date].append({
                'page_url': visit.page_url,
                'duration': visit.duration,
                'timestamp': visit.timestamp,
                'method': visit.method,
                'status_code': visit.status_code,
                'user_agent': visit.user_agent,
                'ip_address': visit.ip_address,
            })

        # Update context for the template
        context.update({
            'title': self.title,
            'total_users': total_users,
            'total_authenticated_users': total_authenticated_users,
            'total_anonymous_users': total_anonymous_users,
            'total_pages_visited': total_pages_visited,
            'total_unique_pages': total_unique_pages,
            'total_time_spent': sum(page['total_time'] for page in page_durations),
            'most_visited_pages': most_visited_pages,
            'least_visited_pages': least_visited_pages,
            'date_categorized_visits': dict(date_categorized_visits),
        })
        return context

class OneDayAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/one_day.html'
    period_hours = 24
    title = "User Activity Analytics for the Last 24 Hours"

class TwoDayAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/two_days.html'
    period_hours = 48
    title = "User Activity Analytics for the Last 2 Days"

    
class ThreeDayAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/three_days.html'
    period_hours = 72
    title = "User Activity Analytics for the Last 3 Days"

class FourDayAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/four_days.html'
    period_hours = 96
    title = "User Activity Analytics for the Last 4 Days"


class FiveDayAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/five_days.html'
    period_hours = 120
    title = "User Activity Analytics for the Last 5 Days"

class SixDayAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/six_days.html'
    period_hours = 144
    title = "User Activity Analytics for the Last 6 Days"

class OneWeekAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/one_week.html'
    period_hours = 168
    title = "User Activity Analytics for the Last Week"

class TwoWeekAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/two_weeks.html'
    period_hours = 336
    title = "User Activity Analytics for the Last 2 Weeks"

class ThreeWeekAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/three_weeks.html'
    period_hours = 24 * 21  # 504 hours
    title = "User Activity Analytics for the Last 3 Weeks"

class OneMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/one_month.html'
    period_hours = 720
    title = "User Activity Analytics for the Last Month"

class TwoMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/two_months.html'
    period_hours = 1440
    title = "User Activity Analytics for the Last 2 Months"

class ThreeMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/three_months.html'
    period_hours = 2160
    title = "User Activity Analytics for the Last 3 Months"

class FourMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/four_months.html'
    period_hours = 2880
    title = "User Activity Analytics for the Last 4 Months"

class FiveMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/five_months.html'
    period_hours = 3600
    title = "User Activity Analytics for the Last 5 Months"

class SixMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/six_months.html'
    period_hours = 4320
    title = "User Activity Analytics for the Last 6 Months"

class SevenMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/seven_months.html'
    period_hours = 5040
    title = "User Activity Analytics for the Last 7 Months"

class EightMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/eight_months.html'
    period_hours = 5760
    title = "User Activity Analytics for the Last 8 Months"

class NineMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/nine_months.html'
    period_hours = 6480
    title = "User Activity Analytics for the Last 9 Months"

class TenMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/ten_months.html'
    period_hours = 7200
    title = "User Activity Analytics for the Last 10 Months"

class ElevenMonthAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/eleven_months.html'
    period_hours = 7920
    title = "User Activity Analytics for the Last 11 Months"

class OneYearAnalyticsView(BaseAnalyticsView):
    template_name = 'users/tracking/one_year.html'
    period_hours = 8760
    title = "User Activity Analytics for the Last Year"


def terms_of_use(request):
    return render(request, 'users/terms_of_use.html')

def privacy_policy(request):
    return render(request, 'users/privacy_policy.html')


def help_center(request):
    return render(request, 'users/help_center.html')


def about(request):
    return render(request, 'users/about.html')
