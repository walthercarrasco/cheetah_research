from django.urls import path
from . import views

urlpatterns = [
    path('info_study/<str:study_id>', views.info_study)
]
