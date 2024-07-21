from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
from google.cloud import storage
from bson import ObjectId
from io import BytesIO
import boto3
import json

GEMINI_API_KEY = settings.GEMINI_API_KEY
db = settings.MONGO_DB 
s3 = boto3.client('s3')

bucket = storage.Client().get_bucket('cactusbucket')
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-1.5-pro')
chats = {}

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
        
        #Select questions to send to chatbot
        selected_questions = []
        for question in questions:
            if "feedback_questions" in question:
                selected_questions.append(
                    {
                        "question": question["question"],
                        "feedback_questions": [fb_question for fb_question in question["feedback_questions"]]
                    }
                )
            else:
                selected_questions.append(
                    {
                        "question": question["question"]
                    }
                )
        print('-------------------')
        print(selected_questions)
        print('-------------------')
        
        #Send instructions to chatbot
        prompt = study['prompt']
        json_data = json.dumps(selected_questions, indent=4)

        chat = model.start_chat(history=[])
        response = chat.send_message(prompt + "Este es una encuesta con preguntas, cada pregunta principal \"question\" puede tener \"feedback_questions\"" 
                          + json_data 
                          + "\nSos un encuestador. A partir de las preguntas recolecta información. Si una pregunta principal tiene "
                          + "\"feedback_questions\" debes hacer esas preguntas inmediatamente después de la pregunta principal." 
                          + "Si una respuesta a las preguntas principales no es clara, hace tus propias preguntas de seguimiento" 
                          + "hasta tener respuestas satisfactorias. No haras preguntas de seguimiento a las \"feedback_questions\"."
                          + "Si la respuesta es clara, continua con la siguiente pregunta. Solamente enviaras preguntas en tus mensajes, "
                          + "no vas a insinuar respuestas para que el usuario conteste. Comenza con la primera pregunta")

        send = {"content":json_data,
                "hash": hash(chat),
                "response": response.text}
        chats[hash(chat)]=chat
        return JsonResponse(send)
    return Response({'error': 'Invalid request method'})

@csrf_exempt
def communicate(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        index = request.POST.get('hash')
        response = (chats[int(index)]).send_message(prompt)
        return JsonResponse({'response': response.text})
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt #ahorita no sirve
def logs(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'})
        filename = f'logs/{study_id}.csv'
        blob = bucket.blob(filename)
        history = chats.history
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