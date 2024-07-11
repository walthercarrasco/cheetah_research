from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
db = settings.MONGO_DB
import urllib.request
import json

# Create your views here.
@csrf_exempt
def createStudy(request):
    date = json.loads(urllib.request.urlopen('http://worldtimeapi.org/api/timezone/America/Tegucigalpa').read())
    if request.method == 'POST':
        body = request.POST
        print(request.POST.get('title'))
        data = {
            'title':body.get('title'),
            'marketTarget':body.get('target'),
            'studyObjetives':body.get('objetive'),
            'studyPrompt':body.get('prompt'),
            'studyDate':date['datetime'],
            'studyStatus':0
        }
        inserted = db['Study'].insert_one(data)
        return JsonResponse({
            'status': 'success',
            'study_id': str(inserted.inserted_id)
        })
    return JsonResponse({'error': 'Invalid request method'})

