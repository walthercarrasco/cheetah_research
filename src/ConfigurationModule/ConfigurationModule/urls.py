"""
URL configuration for ConfigurationModule project.

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
from django.urls import path,include
from createInterviewer.views import createInterviewer, getInterviewer, updateInterviewer

urlpatterns = [
    path('admin/', admin.site.urls),
    path('configuration/', include('Login.urls')),
    path('configuration/', include('createStudy.urls'), name='createStudy'),
    path('configuration/', include('infoStudy.urls'), name='infoStudy'),
    path('configuration/', include('createQuestion.urls'), name='createQuestions'),
    path('configuration/addInterviewer/', createInterviewer, name='createInterviewer'),
    path('configuration/getInterviewer/', getInterviewer, name='getInterviewer'),
    path('configuration/updateInterviewer/', updateInterviewer, name='updateInterviewer'),
    path("configuration/api-auth/", include("rest_framework.urls")),
    path("configuration/api/v1/dj-rest-auth/", include("dj_rest_auth.urls")),
    path('configuration/', include('list_studies.urls'), name='list_studies'),
    path('configuration/', include('summaries.urls'), name='summaries'),
    path('configuration/', include('upload_files.urls'), name='upload_files'),
    path('configuration/', include('deleteStudy.urls'), name='delete'),
    path('configuration/', include('oneTimePasswordForDataAnalysis.urls'), name='oneTimePasswordForDataAnalysis'),
]