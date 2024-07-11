from django.urls import path
from .views import create_study


urlpatterns = [
    path('createStudy/', create_study, name='createStudy'),
]
