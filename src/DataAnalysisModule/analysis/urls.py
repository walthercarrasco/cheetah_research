from django.urls import path
from . import views

urlpatterns = [
    path('analysis/<str:study_id>', views.getAnalysis),
]