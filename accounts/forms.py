from django import forms
from django.contrib.auth.models import User
from .models import EmployeeProfile

class EmployeeSignupForm(forms.ModelForm):
    # Usaremos email y password del user nativo
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = EmployeeProfile
        fields = ['nombre', 'cargo']

    def save(self, commit=True):
        profile = super().save(commit=False)
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        # username = email
        user = User(username=email, email=email)
        user.set_password(password)
        if commit:
            user.save()
            profile.user = user
            profile.save()
        return profile
