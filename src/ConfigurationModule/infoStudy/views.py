from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from bson import ObjectId
import pymongo
db = settings.MONGO_DB

# Create your views here.
def getDate(request, study_id):
    try:
        # Convert study_id to ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid study ID format.'}, status=400)

    try:
        # Fetch the study document from the MongoDB collection
        study = db['Study'].find_one({'_id': study_oid})
        
        if study is None:
            return JsonResponse({'status': 'error', 'message': 'Study not found.'}, status=404)

        # Return the study date
        return JsonResponse({
            'status': 'success',
            'study_date': study.get('studyDate'),
            'studyStatus': study.get('studyStatus')
        })
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Database error.'}, status=500)