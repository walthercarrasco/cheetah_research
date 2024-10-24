from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from bson import ObjectId
db = settings.MONGO_DB

@csrf_exempt
def activateCollection(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        study = db['Study'].find_one({'_id': ObjectId(study_id)})
        status = study['collectionStatus']
        if(status == 0):
            db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 1}})
        if(status == 2):
            db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 3}})
        return JsonResponse({
                                'status': 'activated collection module',
                                'study_id': study_id
                            })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def deactivateCollection(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        study = db['Study'].find_one({'_id': ObjectId(study_id)})
        status = study['collectionStatus']
        if(status == 1):
            db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 0}})
        if(status == 3):
            db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 2}})
        return JsonResponse({
                                'status': 'deactivated collection module',
                                'study_id': study_id
                            })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def activateAnalisis(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        study = db['Study'].find_one({'_id': ObjectId(study_id)})
        status = study['collectionStatus']
        if(status == 0):
            db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 2}})
        if(status == 1):
            db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 3}})
        return JsonResponse({
                                'status': 'activated analisis module',
                                'study_id': study_id
                            })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def deactivateAnalisis(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        study = db['Study'].find_one({'_id': ObjectId(study_id)})
        status = study['collectionStatus']
        if(status == 2):
            db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 0}})
        if(status == 3):
            db['Study'].update_one({'_id': ObjectId(study_id)}, {'$set': {'studyStatus': 1}})
        return JsonResponse({
                                'status': 'activated collection module',
                                'study_id': study_id
                            })
    return JsonResponse({'error': 'Invalid request method'})

