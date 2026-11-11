from django import forms
from .models import Inquiry, Tour


class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        # Remove 'name', 'email', and 'group_type' since they are logged in
        fields = ['phone', 'group_size', 'message']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'field__input', 'placeholder': '+254...'}),
            'group_size': forms.NumberInput(attrs={'class': 'field__input', 'placeholder': 'e.g. 4'}),
            'message': forms.Textarea(attrs={'class': 'field__input', 'rows': 4, 'placeholder': 'Any special requests or dietary needs?'}),
        }


class TourForm(forms.ModelForm):
    class Meta:
        model = Tour
        fields = ['title', 'slug', 'summary', 'description', 'destination', 'duration_days', 'start_date', 'end_date', 'price_from', 'slots_available', 'hero_image', 'is_published', 'is_featured']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'e.g., Holy Land Pilgrimage'}),
            'slug': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'holy-land-pilgrimage'}),
            'summary': forms.Textarea(attrs={'class': 'input-field', 'rows': 2}),
            'description': forms.Textarea(attrs={'class': 'input-field', 'rows': 5}),
            'destination': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'e.g., Israel'}),
            'duration_days': forms.NumberInput(attrs={'class': 'input-field'}),
            'start_date': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
            'price_from': forms.NumberInput(attrs={'class': 'input-field'}),
            'slots_available': forms.NumberInput(attrs={'class': 'input-field'}),
            'hero_image': forms.FileInput(attrs={'class': 'input-field'}),
        }