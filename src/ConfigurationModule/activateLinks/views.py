from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from bson import ObjectId
db = settings.MONGO_DB

@csrf_exempt
def activateCollection(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'collectionStatus': 1}})
        return JsonResponse({
                                'status': 'activated',
                                'study_id': study_id
                            })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def deactivateCollection(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'collectionStatus': 0}})
        return JsonResponse({
                                'status': 'deactivated',
                                'study_id': study_id
                            })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def activateAnalisis(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 1}})
        return JsonResponse({
                                'status': 'activated',
                                'study_id': study_id
                            })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def deactivateAnalisis(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 0}})
        return JsonResponse({
                                'status': 'deactivated',
                                'study_id': study_id
                            })
    return JsonResponse({'error': 'Invalid request method'})

