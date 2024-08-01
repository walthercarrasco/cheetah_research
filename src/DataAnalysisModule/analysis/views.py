from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from bson import ObjectId
from django.views.decorators.csrf import csrf_exempt

db = settings.MONGO_DB


# Create your views here.
@csrf_exempt
def getAnalysis(request, study_id):
    if(request.method != 'GET'):
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
    try:
        # Convert study_id to ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid study ID format.'}, status=400)
    
    try:
        # Fetch the study document from the MongoDB collection
        study = db['Summaries'].find_one({'_id': study_oid})
        if study is None:
            return JsonResponse({'status': 'error', 'message': 'Study not found.'}, status=404)
        
        modules = study.get('modules')
        analysis = {}
        for module in modules:
            analysis[module] = study.get(module)
        
        # Return the analysis data
        return JsonResponse(analysis, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Database error.'}, status=500)
