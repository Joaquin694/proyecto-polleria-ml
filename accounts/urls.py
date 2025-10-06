# accounts/urls.py
from django.urls import path
from .views import LoginView, signup, profile, dashboard
from django.contrib.auth.views import LogoutView

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('signup/', signup, name='signup'),
    path('me/', profile, name='profile'),
    path('dashboard/', dashboard, name='dashboard'),
]
