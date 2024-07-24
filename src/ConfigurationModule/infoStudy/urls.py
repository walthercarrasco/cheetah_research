from django.urls import path
from . import views

urlpatterns = [
    path('info_study/<str:study_id>', views.info_study),
    path('set_status/<str:study_id>', views.setStatus),
    path('get_survey/<str:study_id>', views.getSurvey)
]
