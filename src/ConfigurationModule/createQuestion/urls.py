from django.urls import path
from . import views

urlpatterns = [
    path('createQuestion/<str:study_id>/', views.create_question, name='createQuestion')
]

