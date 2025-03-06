from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField
from ckeditor.widgets import CKEditorWidget
import phonenumbers

from .models import (
    App,
    Feedback,
    FeedbackResponse,
    ApplicationRequest,
    AdminResponse,
    NotificationComment
)

class AppUploadForm(forms.ModelForm):
    description=forms.CharField(widget=CKEditorWidget(config_name='default'))
   
    class Meta:
        model = App
        fields = ['title', 'description', 'thumbails','video', 'category','youtube_link', 'app_file', 'banned','google_drive_link', 'amount','currency']
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'youtube_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter YouTube URL'}),
            'google_drive_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter Google Drive URL'}),
        }


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = [
            'subject',
            'feedback_type',
            'description',
            'priority',
            'attachment',
            'email',
            'url',
            'is_anonymous'
        ]
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a subject'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Provide detailed feedback'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email'
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the relevant URL'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.is_authenticated:
            self.fields['email'].initial = self.user.email
            
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and not instance.is_anonymous:
            instance.user = self.user
            
        # Collect browser information
        if commit:
            instance.save()
        return instance


class FeedbackResponseForm(forms.ModelForm):
    class Meta:
        model = FeedbackResponse
        fields = ['response', 'is_internal']
        widgets = {
            'response': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter your response'
            })
        }

class ApplicationRequestForm(forms.ModelForm):
    phone_number = PhoneNumberField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter phone number with country code (e.g., +1234567890)'}),
    )

    whatsapp_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter WhatsApp number or link (e.g., +1234567890 or https://wa.me/1234567890)'}),
    )

    def clean_whatsapp_number(self):
        value = self.cleaned_data.get("whatsapp_number")
        if not value:
            return value  # Allow empty field

        if value.startswith("http"):
            # Validate as URL
            URLValidator()(value)
        else:
            # Validate as a phone number
            try:
                phone_obj = phonenumbers.parse(value, None)  # Detect region dynamically
                if not phonenumbers.is_valid_number(phone_obj):
                    raise ValidationError("Invalid WhatsApp number")
                # Format number to E.164
                return phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
            except phonenumbers.NumberParseException:
                raise ValidationError("Invalid WhatsApp number format")

        return value  # Return valid value

    class Meta:
        model = ApplicationRequest
        fields = ["app_name", "description", "phone_number", "whatsapp_number"]
        widgets = {
            "app_name": forms.TextInput(attrs={"placeholder": "Enter app name", "class": "form-control"}),
            "description": forms.Textarea(attrs={"placeholder": "Enter description", "class": "form-control", "rows": 3}),
        }



class AdminResponseForm(forms.ModelForm):
    """Form for admin to respond to user application requests"""
    
    class Meta:
        model = AdminResponse
        fields = ["response_text", "response_link", "is_visible"]

    response_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Enter your response here..."}),
        label="Response",
        required=True
    )

    response_link = forms.URLField(
        widget=forms.URLInput(attrs={"placeholder": "Optional: Add a link"}),
        label="Response Link",
        required=False
    )

    is_visible = forms.BooleanField(
        required=False,
        initial=True,
        label="Make Response Visible to User"
    )


class NotificationCommentForm(forms.ModelForm):
    class Meta:
        model = NotificationComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500',
                'rows': '4',
                'placeholder': 'Write your comment here...'
            })
        }