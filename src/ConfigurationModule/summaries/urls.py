from django.urls import path
from . import views

urlpatterns = [
    path('getSummaries/<str:study_id>', views.getSummaries),
    path('forzar/<str:study_id>', views.forzar_analysis),
]