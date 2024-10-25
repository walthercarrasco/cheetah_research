from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.conf import settings
from bson import ObjectId
from django.views.decorators.csrf import csrf_exempt
import boto3

DB = settings.MONGO_DB


s3 = boto3.client('s3',region_name='us-east-1',
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)


# Create your views here.
@csrf_exempt
def getAnalysis(request, study_id):
    if(request.method != 'POST'):
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
    try:
        # Convert study_id to ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid study ID format.'}, status=400)
    body = request.POST
    module = body.get('module')
    filter = body.get('filter')
    sub_module = body.get('sub_module')
    if module is None:
        return JsonResponse({'status': 'error', 'message': 'Module not specified.'}, status=400)
    if filter is None:
        return JsonResponse({'status': 'error', 'message': 'Filter not specified.'}, status=400)
    
    try:
        # Fetch the study document from the MongoDB collection
        study = DB['Summaries'].find_one({'_id': study_oid})
        if study is None:
            return JsonResponse({'status': 'error', 'message': 'Study not found.'}, status=404)
        
        modules = study.get('modules')
        if modules is None:
            return JsonResponse({'status': 'error', 'message': 'Study has no modules.'}, status=400)
        if module not in modules:
            return HttpResponse('Module not available')
        obj = None
        if(module == 'user_personas'):
            obj = s3.get_object(Bucket='cheetahresearchlogs ', Key=f"analysis/{study_id}/user_personas/{filter}.md")
        else:
            obj = s3.get_object(Bucket='cheetahresearchlogs ', Key=f"analysis/{study_id}/{module}/{sub_module}/{filter}.md")
        content = obj['Body'].read()
        return HttpResponse(content)
    except Exception as e:
        return HttpResponse('Module not available')
