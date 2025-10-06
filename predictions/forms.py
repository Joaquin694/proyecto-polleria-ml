from django import forms
from .models import PredictionRun

class UploadCSVForm(forms.ModelForm):
    class Meta:
        model = PredictionRun
        fields = ['model_choice', 'uploaded_csv']
