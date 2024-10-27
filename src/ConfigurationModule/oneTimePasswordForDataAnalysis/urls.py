# urls.py
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from . import views

urlpatterns = [
    path('api/generate-otp/', views.generate_otp, name='generate-otp'),
    path('api/validate-otp/', views.validate_otp, name='validate-otp'),
    path('api/get-otp/', views.get_otp, name='get-otp'),
]