from django.urls import path
from .views import upload_and_predict, run_results, runs_history

app_name = 'predictions'
urlpatterns = [
    path('', upload_and_predict, name='upload'),
    path('runs/', runs_history, name='history'),
    path('runs/<int:run_id>/', run_results, name='run_results'),
]
