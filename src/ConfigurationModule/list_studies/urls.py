from django.urls import path
from . import views

urlpatterns = [
    path('get_studies/', views.get_studies),
]