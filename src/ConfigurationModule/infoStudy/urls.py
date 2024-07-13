from django.urls import path
from . import views

urlpatterns = [
    path('getDate/<str:study_id>', views.getDate)
]
