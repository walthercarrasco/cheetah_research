from django.urls import path
from .views import createStudy


urlpatterns = [
    path('createStudy/', createStudy, name='createStudy'),
]
