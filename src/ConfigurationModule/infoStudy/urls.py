from django.urls import path
from . import views

urlpatterns = [
    path('info_study/<str:study_id>', views.info_study),
    path('set_status/<str:study_id>/<str:statu>', views.setStatus),
    path('get_survey/<str:study_id>', views.getSurvey),
    path('filters/<str:study_id>', views.setFilters),
    path('modules/<str:study_id>', views.setModules),
    path('test/<str:study_id>/<str:test>', views.setTest),
    path('test/<str:study_id>', views.getTest),
]
