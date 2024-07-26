from django.urls import path
from . import views

urlpatterns = [
    path('getSummaries/<str:study_id>', views.getSummaries),
]