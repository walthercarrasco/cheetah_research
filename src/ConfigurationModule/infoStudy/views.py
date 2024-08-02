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
def setStatus(request, study_id, statu):
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
        if int(statu) == 2:
            try:
                response = urllib.request.urlopen('http://worldtimeapi.org/api/timezone/America/Tegucigalpa')
                enddate = json.loads(response.read())
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': 'Error al obtener la fecha desde la API.'}, status=500)
            db['Study'].update_one({'_id': study_oid}, {'$set': {'end_date': enddate['datetime']}})
        db['Study'].update_one({'_id': study_oid}, {'$set': {'studyStatus': int(statu)}})
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
        survey['study_id'] = study_id
        return JsonResponse(survey)
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)
    
@csrf_exempt
def setFilters(request, study_id):
    if(request.method != 'POST'):
        return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)
    filters = request.POST.get('filters')
    if(filters is None):
        return JsonResponse({'status': 'error', 'message': 'Missing filters parameter.'}, status=400)
    
    try:
        # Convertir study_id a ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Formato de ID de estudio inválido.'}, status=400)
    
    try:
        filters = json.loads(filters)  # Deserializar la cadena JSON a un array
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
    
    try:
        db['Surveys'].update_one({'_id': study_oid}, {'$set': {'filters': filters}})
        return JsonResponse({'status': 'success'})
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)

@csrf_exempt
def setModules (request, study_id):
    if(request.method != 'POST'):
        return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)
    if('modules' not in request.POST):
        return JsonResponse({'status': 'error', 'message': 'Missing modules parameter.'}, status=400)
    try:
        # Convertir study_id a ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Formato de ID de estudio inválido.'}, status=400)
    
    try:
        modules = json.loads(request.POST.get('modules'))  # Deserializar la cadena JSON a un array
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)    
    
    try:
        db['Summaries'].insert_one({'_id': study_oid, 'modules': modules})
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)
    return JsonResponse({'status': 'success'})

@csrf_exempt
def setTest(request, study_id, test):
    if(request.method != 'PUT'):
        return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)
    if(test is None):
        return JsonResponse({'status': 'error', 'message': 'Missing test parameter.'}, status=400)
    if(test not in ['0', '1']):
        return JsonResponse({'status': 'error', 'message': 'Invalid test parameter.'}, status=400)
    try:
        # Convertir study_id a ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Formato de ID de estudio inválido.'}, status=400)
    flag = True
    if(test == '0'):
        flag = False
    try:
        db['Surveys'].update_one({'_id': study_oid}, {'$set': {'test': flag}})
        return JsonResponse({'status': 'success'})
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)
    
@csrf_exempt
def getTest(request, study_id):
    if(request.method != 'GET'):
        return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)
    try:
        # Convertir study_id a ObjectId
        study_oid = ObjectId(study_id)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Formato de ID de estudio inválido.'}, status=400)
    try:
        survey = db['Surveys'].find_one({'_id': study_oid})
        if survey is None:
            return JsonResponse({'status': 'error', 'message': 'Estudio no encontrado.'}, status=404)
        return JsonResponse({'status': 'success', 'test': survey.get('test')})
    except pymongo.errors.PyMongoError as e:
        return JsonResponse({'status': 'error', 'message': 'Error en la base de datos.'}, status=500)