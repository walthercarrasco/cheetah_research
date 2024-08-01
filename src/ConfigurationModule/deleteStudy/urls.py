from django.urls import path
from .views import delete_study

urlpatterns = [
    path('deleteStudy/', delete_study, name='deleteStudy'),
]