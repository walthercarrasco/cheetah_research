from django.shortcuts import render
from rest_framework import generics
from .models import Interviewer
from .serializer import InterviewerSerializer

class InterviewerListCreate(generics.ListCreateAPIView):
    queryset = Interviewer.objects.all()
    serializer_class = InterviewerSerializer

