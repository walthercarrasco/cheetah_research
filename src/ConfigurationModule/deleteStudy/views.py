from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import urllib.request
from bson import ObjectId
import json
import pymongo

db = settings.MONGO_DB
@csrf_exempt
def delete_study(request):
    if request.method == 'DELETE':
        try:

            data = json.loads(request.body)
            study_id = data.get('study_id')

            if not study_id or not ObjectId.is_valid(study_id):
                return JsonResponse({'status': 'error', 'message': 'Invalid study'}, status=400)

            study = db['Study'].find_one({'_id': ObjectId(study_id)})
            if not study:
                return JsonResponse({'status': 'error', 'message': 'Study not found.'}, status=404)

            db['Study'].delete_one({'_id': ObjectId(study_id)})

            db['Surveys'].delete_many({'_id': ObjectId(study_id)})
            db['Interviewer'].delete_many({'_id': ObjectId(study_id)})
            db['Summaries'].delete_many({'_id': ObjectId(study_id)})
            db['survey_logs'].delete_many({'_id': ObjectId(study_id)})
            db['Surveys'].delete_many({'_id': ObjectId(study_id)})

            return JsonResponse({'status': 'success', 'message': 'Study deleted.'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except pymongo.errors.PyMongoError:
            return JsonResponse({'status': 'error', 'message': 'Database error'}, status=500)

    else :
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
