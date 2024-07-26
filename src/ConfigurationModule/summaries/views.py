from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from bson import ObjectId
import json

db = settings.MONGO_DB

@csrf_exempt
def getSummaries(request, study_id):
    if request.method == 'GET':
        try:
            summaries = db['Summaries'].find_one({'_id': ObjectId(study_id)})
            if summaries:
                summaries.pop('_id')
                return JsonResponse(summaries, safe=False)
            else:
                return JsonResponse({'status': 'fail', 'message': 'No summaries found'})
        except Exception as e:
            return JsonResponse({'status': 'fail', 'message': str(e)})
    else:
        return JsonResponse({'status': 'fail', 'message': 'Invalid method'})