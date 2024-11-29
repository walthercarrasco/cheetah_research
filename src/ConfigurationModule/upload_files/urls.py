from django.urls import path
from . import views

urlpatterns = [
    path('upload_files/<str:study_id>', views.upload_files, name='upload_files'),
    path('upload_md/<str:study_id>', views.upload_md, name='upload_md'),
]