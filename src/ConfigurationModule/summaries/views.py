from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from bson import ObjectId
import json
import google.generativeai as genai
import boto3
import os
import chardet
from datetime import datetime

GEMINI_API_KEY = settings.GEMINI_API_KEY
DB = settings.MONGO_DB

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

s3 = boto3.client('s3',region_name='us-east-1',
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

@csrf_exempt
def getSummaries(request, study_id):
    if(request.method != 'POST'):
        return JsonResponse({'status': 'fail', 'message': 'Invalid method'}, status=400)
    try:
        study_oid = ObjectId(study_id)
    except:
        return JsonResponse({'status': 'fail', 'message': 'Invalid study id'}, status=400)
    if(DB['Study'].find_one({'_id': study_oid}) is None):
        return JsonResponse({'status': 'fail', 'message': 'Study not found'}, status=404)
    body = request.POST
    module = body.get('module')
    filter = body.get('filter')
    sub_module = body.get('sub_module')
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
            obj = s3.get_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md")
            content = obj['Body'].read()
            return HttpResponse(content)
        elif(module == "individual_questions"):
            if(sub_module != "individual_narrative" and sub_module != "percentage"):
                JsonResponse({'status': 'fail', 'message': 'Invalid sub_module'})
            obj = s3.get_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md")
            content = obj['Body'].read()
            return HttpResponse(content)
        elif(module == "user_personas"):
            obj = s3.get_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{filter}.md")
            content = obj['Body'].read()
            return HttpResponse(content)
        elif(module == "psicographic_questions"):
            obj = s3.get_object(Bucket='cheetahresearchlogs', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md")
            content = obj['Body'].read()
            return HttpResponse(content)
        else:
            return JsonResponse({'status': 'fail', 'message': 'Invalid module'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'fail', 'message': str(e)}, status=500)    
    
    
    
# @csrf_exempt
# def setSummary(request, study_id):
#     if request.method != 'PUT':
#         return JsonResponse({'status': 'fail', 'message': 'Invalid method'})
#     if(request.POST.get('filter') is None):
#         return JsonResponse({'status': 'fail', 'message': 'No filter provided'})
#     if(request.POST.get('module') is None):
#         return JsonResponse({'status': 'fail', 'message': 'No module provided'})
#     if(request.POST.get('prompt') is None):
#         return JsonResponse({'status': 'fail', 'message': 'No prompt provided'})
#     study = DB['Study'].find_one({'_id': ObjectId(study_id)})
    
#     if(study is None):
#         return JsonResponse({'status': 'fail', 'message': 'Study not found'})
    
#     filter = request.POST.get('filter')
#     module = request.POST.get('module')
#     prompt = request.POST.get('prompt')
#     sub_module = request.POST.get('sub_module')    
#     try:
#         s3 = boto3.client('s3',region_name='us-east-1',
#                             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#                             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        
#         key = f"surveys/{study_id}/"
#         objects = s3.list_objects_v2(Bucket='cheetahresearchlogs', Prefix=key)
#         files = []
#         if 'Contents' in objects:
#             key_files = [item['Key'] for item in objects['Contents'] if item['Key'] != key]
#             if not os.path.exists(f"./storage/{study_id}/"):
#                 os.makedirs(f"./storage/{study_id}/")
#             for file_key in key_files:
#                 path = f"./storage/{study_id}/{file_key.split('/')[-1]}"
#                 file_obj = s3.get_object(Bucket=os.environ['BUCKET_NAME'], Key=file_key)
#                 if file_obj["ContentType"] == "application/pdf":
#                     s3.download_file(os.environ['BUCKET_NAME'], file_key, path)
#                     files.append(genai.upload_file(path))
#                 else:
#                     csv_body = file_obj["Body"].read()
#                     result_encoding = chardet.detect(csv_body)
#                     csv_content = csv_body.decode(result_encoding['encoding'])
#                     with open(path, 'wb') as f:
#                         f.write(csv_content.encode('utf-8'))
#                     files.append(genai.upload_file(path))
#         else:
#             return JsonResponse({'status': 'fail', 'message': 'No files found'})
#         main_promt(prompt, module, filter, study_id, study, sub_module, files)
        
#         return JsonResponse({'status': 'success', 'message': 'Summary set successfully'})
#     except Exception as e:
#         return JsonResponse({'status': 'fail', 'message': str(e)})

def forzar_analysis(request, study_id):
    try:
        studyoid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'fail'}, status=400)
    if(DB['Study'].find_one({'_id': studyoid}) is None):
        return JsonResponse({'status': 'fail'}, status=404)
    DB['survey_logs'].update_one({'_id': studyoid }, {'$set': {'last_update': datetime.now()}}, upsert=True)
    return JsonResponse({'status': 'success'})