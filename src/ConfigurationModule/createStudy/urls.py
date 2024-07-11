from django.urls import path
from .views import createStudy


urlpatterns = [
    path('', createStudy, name='createStudy'),
]
