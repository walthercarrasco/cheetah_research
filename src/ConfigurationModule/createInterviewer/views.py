from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from google.cloud import storage

import os
db = settings.MONGO_DB
#Acceso al bucket en GCP
bucket = storage.Client().get_bucket('bucket_cheetah')

#Crear Entrevistador
@csrf_exempt
def createInterviewer(request):
    if request.method == 'POST':
        body = request.POST
        filename = None
        #Conseguir Parametros 
        if(request.FILES):
            #Subir foto de perfil
            image_file = request.FILES['interviewerProfilePicture']
            studyId = body.get('studyId')
            filename = f'pfp/{studyId}/'+image_file.name
            blob = bucket.blob(filename)
            blob.upload_from_file(image_file)
        data = {
            'interviewerName':body.get('interviewerName'),
            'interviewerProfilePicture':filename,
            'interviewerTone':body.get('interviewerTone'),
            'interviewerGreeting':body.get('interviewerGreeting'),
            'importantObservation':body.get('importantObservation'),
            'studyId':body.get('studyId')
        }
        #Subir a la base de datos
        post = db['Interviewer'].insert_one(data)
        
        return JsonResponse({
            'status': 'success',
            'interviewer_id': str(post.inserted_id)
        })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
#Conseguir Info de Entrevistador con uuid
def getInterviewer(request):
    if request.method == 'POST':
        #Buscar Entrevistador en base de datos
        interviewer = db['Interviewer'].find_one({'studyId': request.POST['studyId']})
        pfp = interviewer.get('interviewerProfilePicture')
        blob = bucket.blob(pfp) #archivo de foto de perfil
        #Retornar Informacion
        return JsonResponse({
            'interviewers': [
                {
                    'interviewer_id': str(interviewer['_id']),
                    'interviewerName': interviewer['interviewerName'],
                    'interviewerProfilePicture': pfp,
                    'interviewerTone': interviewer['interviewerTone'],
                    'interviewerGreeting': interviewer['interviewerGreeting'],
                    'studyId': interviewer['studyId']
                } 
            ]
        })
    return JsonResponse({'error': 'Invalid request method'})

#Conseguir foto de perfil de bucket (no 100% funcional)
def getInterviewerPfp(request):
    if request.method == 'POST':
        interviewer = db['Interviewer'].find_one({'studyId': request.POST['studyId']})
        pfp = interviewer.get('interviewerProfilePicture')
        blob = bucket.blob(pfp)
    return JsonResponse({'error': 'Invalid request method'})
