from .models import CustomUser
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Profile


class CustomUserCreationForm(UserCreationForm):
    email=forms.EmailField(required=True)
   
    class Meta(UserCreationForm.Meta):
        model=CustomUser
        fields=['username', 'email', 'password1', 'password2']


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'photo', 'is_contributor']
        widgets = {
            'bio': forms.Textarea(attrs={
                'placeholder': 'Tell us about yourself...',
                'class': 'form-control'
            }),
            'is_contributor': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }