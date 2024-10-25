from django.urls import path
from . import views


urlpatterns = [
    path('createStudy/', views.create_study, name='createStudy'),
    path('updateStudy/<str:study_id>', views.update_study)
]
