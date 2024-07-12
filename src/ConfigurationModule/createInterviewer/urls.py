from django.urls import path
from .views import createInterviewer


urlpatterns = [
    path('interviewer/', createInterviewer, name='createInterviewer'),
]