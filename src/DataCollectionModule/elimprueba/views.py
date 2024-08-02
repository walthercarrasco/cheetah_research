from django.shortcuts import render

# Create your views here.

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
from bson import ObjectId
from datetime import datetime
import boto3
import json
import pandas as pd
from io import StringIO
import chardet

s3 = boto3.client('s3',
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
db = settings.MONGO_DB
bucket_name = settings.BUCKET_NAME

@csrf_exempt
def elimTest(request):
    if request.method == 'POST':
        _id = request.POST['study_id']
        study = db['Study'].find_one({'_id': ObjectId(_id)})
        if study is None:
            return JsonResponse({'status': 'error', 'message': 'Study not found'})
        
        folder_prefix = f"surveys/{_id}/"
        objects_to_delete = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_prefix)

        # Check if there are objects to delete
        if 'Contents' in objects_to_delete:
            delete_keys = [{'Key': obj['Key']} for obj in objects_to_delete['Contents']]

            # Delete the objects
            s3.delete_objects(Bucket=bucket_name, Delete={'Objects': delete_keys})

            print(f'Folder {folder_prefix} deleted successfully.')
        return JsonResponse({'status': 'deleted successfully'})