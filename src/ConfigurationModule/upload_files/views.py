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

@csrf_exempt
def upload_md(request, study_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    if request.FILES.items() is None:
        return JsonResponse({'error': 'No files provided'}, status=400)
    study = DB['Study'].find_one({'_id' : ObjectId(study_id)})
    if study is None:
        return JsonResponse({'error': 'Study not found'}, status=404)
    body = request.POST
    module = body.get('module')
    filter = body.get('filter')
    sub_module = body.get('sub_module')
    files = request.FILES.items()
    file_content = None
    for key,file in files:
        file_content = file.read()
    if(module is None):
        return JsonResponse({'status': 'fail', 'message': 'No module provided'}, status=400)
    if(filter is None):
        return JsonResponse({'status': 'fail', 'message': 'No filter provided'}, status=400)
    if(sub_module is None and module != "user_personas"):
        return JsonResponse({'status': 'fail', 'message': 'No sub_module provided'}, status=400)
    
    try:        
        if(module == "general"):
            if(sub_module != "narrative" and sub_module != "factual"):
                JsonResponse({'status': 'fail', 'message': 'Invalid sub_module'})
            s3.put_object(Bucket=bucket_name, Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md", Body=file_content, ContentType=file.content_type)
        elif(module == "individual_questions"):
            if(sub_module != "individual_narrative" and sub_module != "percentage"):
                JsonResponse({'status': 'fail', 'message': 'Invalid sub_module'})
            s3.put_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md", Body=file_content, ContentType=file.content_type)
        elif(module == "user_personas"):
            s3.put_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{filter}.md", Body=file_content, ContentType=file.content_type)
        elif(module == "psicographic_questions"):
            s3.put_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md", Body=file_content, ContentType=file.content_type)
        else:
            return JsonResponse({'status': 'fail', 'message': 'Invalid module'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'fail', 'message': 'error to put object on s3'}, status=500)

    return JsonResponse({'status': 'success'}, status=200)