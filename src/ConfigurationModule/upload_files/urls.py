from django.urls import path
from . import views

urlpatterns = [
    path('upload_files/<str:study_id>/', views.upload_files, name='upload_files')
]