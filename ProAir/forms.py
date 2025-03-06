# forms.py
from django import forms
from .models import Middle

class MiddleForm(forms.ModelForm):
    class Meta:
        model = Middle
        fields = ['title', 'description', 'thumbails', 'category', 
                 'send_notification']
        widgets = {
            'send_notification': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }