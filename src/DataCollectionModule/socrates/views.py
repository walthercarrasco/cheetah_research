from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
from bson import ObjectId
from datetime import datetime, timedelta
import boto3
import json
import io

GEMINI_API_KEY = settings.GEMINI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')