from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
from bson import ObjectId
import boto3
import json

GEMINI_API_KEY = settings.GEMINI_API_KEY
db = settings.MONGO_DB 
s3 = boto3.client('s3')

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
                          + "\nEres un entrevistador. Genera una línea para continuar la conversación sobre las preguntas descritas a continuación. Necesitamos "
                          + "discutir todas las preguntas de manera coherente (mensaje por mensaje), así que no hagas más de una pregunta en el mensaje."
                          + "Si el diálogo ya tiene información sobre todas las preguntas, formula una pregunta de profundización para obtener una respuesta más " 
                          + "detallada (posible redacción: \"Cuéntame más sobre...\", \"¿Qué más...\", \"¿Cómo...\", \"¿Por qué...\", \"¿Qué quieres decir con...\", \"Aclara...\", " 
                          + "\"¿Qué exactamente...\", etc.). No haras preguntas de seguimiento a las \"feedback_questions\"."
                          + "Si al respondedor le resulta difícil o no sabe, pídele que adivine lo que piensa o siente."
                          + "No sugieras respuestas, no ofrezcas opciones de respuesta, no inventes respuestas para el respondedor. Comenza con la primera pregunta."
                          + "Mantén el tono de la conversación del diálogo en curso. En cuanto termines la encuesta, escribi 'LISTO' para finalizar la conversación.")

        send = {"content":selected_questions,
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
        if response.text.__contains__('LISTO'):
            chats.pop(int(index))
        return JsonResponse({'response': response.text})
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt #ahorita no sirve
def logs(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'})
        filename = f'logs/{study_id}.csv'
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
        
        return JsonResponse({'response': survey})
    return JsonResponse({'error': 'Invalid request method'})