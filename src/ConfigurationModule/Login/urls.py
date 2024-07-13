from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.user_login, name='user_login'),
    path('home/', views.home, name='home'),
    path('register/', views.user_register, name='user_register'),
    path('register/password-reset', views.password_reset_request, name='password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('', views.user_logout, name='user_logout'),
]