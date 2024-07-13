from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from google.cloud import storage

import os
db = settings.MONGO_DB
bucket = storage.Client().get_bucket('cactusbucket')

@csrf_exempt
def createInterviewer(request):
    if request.method == 'POST':
        body = request.POST
        filename = None
        if(request.FILES):
            image_file = request.FILES['interviewerProfilePicture']
            filename = f'pfp/{body.get('surveyId')}/'+image_file.name
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
        post = db['Interviewer'].insert_one(data)
        
        return JsonResponse({
            'status': 'success',
            'interviewer_id': str(post.inserted_id)
        })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def getInterviewer(request):
    if request.method == 'POST':
        interviewer = db['Interviewer'].find_one({'studyId': request.POST['studyId']})
        pfp = interviewer.get('interviewerProfilePicture')
        blob = bucket.blob(pfp)
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

def getInterviewerPfp(request):
    if request.method == 'POST':
        interviewer = db['Interviewer'].find_one({'studyId': request.POST['studyId']})
        pfp = interviewer.get('interviewerProfilePicture')
        blob = bucket.blob(pfp)
    return JsonResponse({'error': 'Invalid request method'})
