from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from bson import ObjectId
import urllib.request
import json
import pymongo

# Get the MongoDB database
db = settings.MONGO_DB

@csrf_exempt
def create_study(request):
    if request.method == 'POST':
        try:
            response = urllib.request.urlopen('http://worldtimeapi.org/api/timezone/America/Tegucigalpa')
            date = json.loads(response.read())
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Error fetching date from API.'}, status=500)

        if request.method == 'POST':
            body = request.POST
            
            title = body.get('title')
            target = body.get('target')
            objective = body.get('objective')
            prompt = body.get('prompt')

            if not title or not target or not objective or not prompt:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields.'}, status=400)

            data = {
                'title': title,
                'marketTarget': target,
                'studyObjectives': objective,
                'studyDate': date['datetime'],
                'studyStatus': 0
            }

            try:
                inserted = db['Study'].insert_one(data)
                db['Surveys'].insert_one({'study_id': inserted.inserted_id,'prompt': prompt, 'questions': []})
                return JsonResponse({
                    'status': 'success',
                    'study_id': str(inserted.inserted_id)
                })
            except pymongo.errors.PyMongoError as e:
                return JsonResponse({'status': 'error', 'message': 'Database error.'}, status=500)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)