from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from bson import ObjectId
import boto3
import json
import threading

db = settings.MONGO_DB 
s3 = boto3.client('s3', 
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
bucket_name = settings.BUCKET_NAME
bucket_url = settings.BUCKET_URL

@csrf_exempt
def create_question(request, study_id):
    if request.method == 'POST':
        try:
            questions = json.loads(request.POST.get('questions'))
            files = request.FILES.items()
            saveQuestions(questions, study_id, files)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'fail', 'message': str(e)})
    else:
        return JsonResponse({'status': 'fail', 'message': 'Invalid method'})

def saveQuestions(questions, study_id, files):
    # Procesar y almacenar las preguntas en la base de datos
    file_tasks = []
    for key, value in files:
        path = f"images/{study_id}/{key}.{value.name.split('.')[-1]}"
        questions[int(key) - 1]['file_path'] = path
        # Read file content into memory
        file_content = value.read()
        # Create a thread to upload the file content
        file_task = threading.Thread(target=upload_file_to_bucket, args=(path, file_content, value.content_type))
        file_tasks.append(file_task)
        file_task.start()

    # Save the questions to the database
    db['Surveys'].update_one({'_id': ObjectId(study_id)}, {'$set': {'questions': questions}})

def upload_file_to_bucket(path, file_content, content_type):
    extension = path.split('.')[-1]
    s3.put_object(Bucket=bucket_name, Key=path, Body=file_content, ContentType=content_type)
    s3.put_object_acl(ACL='public-read', Bucket=bucket_name, Key=path)