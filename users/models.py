import requests
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils.timezone import now
import json
from django.db import models
from django.utils.timezone import now


from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.timezone import now
import requests
import json

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.timezone import now
import requests
import json

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  
    username = models.CharField(
        max_length=150,
        validators=[RegexValidator(r'^[\w\s]+$')]
    )
    registration_date = models.DateTimeField(default=now)

    # New fields
    continent = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city_or_region = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    devices_used = models.JSONField(default=list, blank=True)  # Store as a list of device names/types

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']


    def save(self, *args, **kwargs):
        # If IP address is set, use it to populate geo fields
        if self.ip_address:
            try:
                # Call ipstack API
                response = requests.get(
                    f"http://api.ipstack.com/{self.ip_address}?access_key=2066aa1BQZKqdp2CV3QV5nUEsqSg1ygegLmqRygj"
                )
                if response.status_code == 200:
                    data = response.json()
                    self.country = data.get("country_name", "")
                    self.city_or_region = data.get("city", "")
                    self.district = data.get("region_name", "")
                    self.continent = data.get("continent_name", "")
            except Exception as e:
                print(f"Error fetching geo data: {e}")
        
        # Ensure devices_used is always a list
        if not isinstance(self.devices_used, list):
            try:
                self.devices_used = json.loads(self.devices_used)
            except Exception as e:
                self.devices_used = []
                print(f"Error parsing devices_used: {e}")
        
        super().save(*args, **kwargs)

class Profile(models.Model):
    user=models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    bio=models.TextField()
    photo=models.ImageField(upload_to='profile-picture/')
    is_contributor = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {'Contributor' if self.is_contributor else 'User'}"


class UserActivity(models.Model):
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=40)
    start_time = models.DateTimeField(default=now)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Activities"
        unique_together = ('user', 'session_id')

    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.session_id[:8]}"

    @property
    def total_duration(self):
        return (self.last_activity - self.start_time).total_seconds()

class PageVisit(models.Model):
    activity = models.ForeignKey(UserActivity, on_delete=models.CASCADE)
    page_url = models.CharField(max_length=2000)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField(help_text='Duration in seconds')
    method = models.CharField(max_length=100)
    status_code = models.IntegerField()
    user_agent = models.TextField()
    ip_address = models.GenericIPAddressField()

    def __str__(self):
        return f"{self.page_url} - {self.timestamp}"

class DailyReport(models.Model):
    date = models.DateField(auto_now_add=True, unique=True)
    unique_users = models.PositiveIntegerField(default=0)
    total_visits = models.PositiveIntegerField(default=0)
    unique_pages = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Daily Reports'
        ordering = ['-date']
