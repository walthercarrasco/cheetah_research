from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import boto3
from django.conf import settings
from bson import ObjectId
from datetime import datetime

DB = settings.MONGO_DB
s3 = boto3.client('s3', 
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
bucket_name = settings.BUCKET_DATA

# Create your views here.
@csrf_exempt
def upload_files(request, study_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    if request.FILES.items() is None:
        return JsonResponse({'error': 'No files provided'}, status=400)
    study = DB['Study'].find_one({'_id' : ObjectId(study_id)})
    if study is None:
        return JsonResponse({'error': 'Study not found'}, status=404)
    files = request.FILES.items()
    for key,file in files:
        file_content = file.read()
        s3.put_object(Bucket=bucket_name, Key=f"surveys/{study_id}/info_{file.name}", Body=file_content, ContentType=file.content_type)
    DB['survey_logs'].update_one({'_id': ObjectId(study_id)}, {'$set': {'last_update': datetime.now()}}, upsert=True)
    return JsonResponse({'status': 'success'})