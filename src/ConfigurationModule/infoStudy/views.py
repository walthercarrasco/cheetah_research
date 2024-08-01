from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from bson import ObjectId
from django.views.decorators.csrf import csrf_exempt
import pymongo
import urllib.request
import json

# Connect to MongoDB
db = settings.MONGO_DB

# Create your views here.
def info_study(request, study_id):
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
            'studyDate': study.get('studyDate'),
            'studyStatus': study.get('studyStatus')
        })
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Database error.'}, status=500)
    
@csrf_exempt
def setStatus(request, study_id):
    try:
        # Convertir study_id a ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Formato de ID de estudio inválido.'}, status=400)

    try:
        # Obtener el documento del estudio desde la colección de MongoDB
        study = db['Study'].find_one({'_id': study_oid})
        
        if study is None:
            return JsonResponse({'status': 'error', 'message': 'Estudio no encontrado.'}, status=404)

        # Actualizar el estado del estudio
        if request.POST['studyStatus'] == 2:
            try:
                response = urllib.request.urlopen('http://worldtimeapi.org/api/timezone/America/Tegucigalpa')
                enddate = json.loads(response.read())
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': 'Error al obtener la fecha desde la API.'}, status=500)
            db['Study'].update_one({'_id': study_oid}, {'$set': {'end_date': enddate['datetime']}})
        db['Study'].update_one({'_id': study_oid}, {'$set': {'studyStatus': request.POST['studyStatus']}})
        return JsonResponse({'status': 'success'})
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)

@csrf_exempt
def getSurvey(request, study_id):
    try:
        # Convertir study_id a ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Formato de ID de estudio inválido.'}, status=400)
    try:
        # Obtener el documento del estudio desde la colección de MongoDB
        survey = db['Surveys'].find_one({
            '_id': study_oid
        })
        if survey is None:
            return JsonResponse({'status': 'error', 'message': 'Estudio no encontrado.'}, status=404)
        survey.pop('_id')
        survey.append({'study_id': study_id})
        return JsonResponse(survey)
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)
    
@csrf_exempt
def setFilters(request, study_id):
    if(request.method != 'POST'):
        return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)
    if('filters' not in request.POST):
        return JsonResponse({'status': 'error', 'message': 'Missing filters parameter.'})
    try:
        # Convertir study_id a ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Formato de ID de estudio inválido.'}, status=400)
    try:
        db['Surveys'].update_one({'_id': study_oid}, {'$set': {'filters': request.POST['filters']}})
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)

@csrf_exempt
def setModules (request, study_id):
    if(request.method != 'POST'):
        return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)
    if('modules' not in request.POST):
        return JsonResponse({'status': 'error', 'message': 'Missing modules parameter.'})
    try:
        # Convertir study_id a ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Formato de ID de estudio inválido.'}, status=400)
    try:
        db['Summaries'].insert_one({'_id': study_oid, 'modules': request.POST['modules']})
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)
    return JsonResponse({'status': 'success'})