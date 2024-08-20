"""
URL configuration for DataCollectionModule project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from chatbot.views import communicate, logs, start, download_logs, updateLogs
from elimprueba.views import elimTest
urlpatterns = [
    path('admin/', admin.site.urls),
    path('chatbot/communicate/', communicate),
    path('chatbot/logs/', logs),
    path('chatbot/start/', start),
    path('elimTest/', elimTest),
    path('chatbot/download_logs/', download_logs),
    path('chatbot/updateLogs/', updateLogs),
]
