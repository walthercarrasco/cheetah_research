from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
from google.cloud import storage
from bson import ObjectId
import json

GEMINI_API_KEY = settings.GEMINI_API_KEY
db = settings.MONGO_DB 
bucket = storage.Client().get_bucket('cactusbucket')
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-1.5-pro')
chat = model.start_chat(history=[])

@csrf_exempt
def start(request):
    if request.method == 'POST':
        #Get study_id from request
        study_id = request.POST['study_id']
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'})
        
        #Get study from database
        study = db['Surveys'].find_one({'study_id': ObjectId(study_id)})
        if study is None:
            return JsonResponse({'error': 'Study not found'})
        
        #Get questions from study
        questions = study['questions']
        list = []
        for q in questions:
            list.append(q['question'])
        send = {"questions": list}
        
        #Send instructions to chatbot
        prompt = study['prompt']
        instructions = 'Recibiras mensajes de forma "pregunta: respuesta", enviaras preguntas de seguimiento para recolectarmas informacion si la respuesta recibida no es clara. Con una respuesta clara. Enviaras "LISTO" para continuar con la siguiente pregunta.'
        final = prompt + '\n' + instructions
        chat.send_message(final)
        return JsonResponse(send)
    return Response({'error': 'Invalid request method'})

@csrf_exempt
def communicate(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        response = chat.send_message(prompt)
        return JsonResponse({'response': response.text})
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def logs(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'})
        filename = f'logs/{study_id}.csv'
        blob = bucket.blob(filename)
        history = chat.history
        history = history[2:]
        survey = '"'
        for message in history:
            if(message.role == 'user'):
                answer = message.parts[0].text.replace("\n", " ")
                if answer.__contains__("|"):
                    answer = answer.split("|")[1]
                survey += answer+','
            if(message.role == 'model'):
                if(message.parts[0].text.__contains__('LISTO')):
                    survey = survey[:-1]
                    survey += '","'
            print(message.role)
            print(message.parts[0].text)
            print('-------------------------------')
        survey = survey[:-2]
        survey.replace("\n", " ")
        print(survey)
        with blob.open(mode='w') as f:
            f.write(survey)
        return JsonResponse({'response': survey})
    return JsonResponse({'error': 'Invalid request method'})