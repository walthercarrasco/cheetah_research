from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
from bson import ObjectId
from datetime import datetime, timedelta
import boto3
import json

GEMINI_API_KEY = settings.GEMINI_API_KEY
db = settings.MONGO_DB 
db = settings.MONGO_DB
s3 = boto3.client('s3', 
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
bucket_name = settings.BUCKET_NAME
bucket_url = settings.BUCKET_URL
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-1.5-pro')
chats = {}
picMap = {}
urlMap = {}
questionsForHistory = {}
startTimes = {}

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
        questionsWithUrl = []
        questionWithPic = []
        allQuestions = []
        for question in questions:
            allQuestions.append(question["question"])
            
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
                
            if "picture" in question:
                questionWithPic.append(
                    {
                        "question": question["question"],
                        "picture": question["picture"]
                    }
                )
                
            if "url" in question:
                questionsWithUrl.append(
                    {
                        "question": question["question"],
                        "url": question["url"]
                    }
                )
                
        #Send instructions to chatbot
        prompt = study['prompt']
        json_data = json.dumps(selected_questions, indent=4)

        chat = model.start_chat(history=[])
        response = chat.send_message(prompt + "Este es una encuesta con preguntas, cada pregunta principal \"question\" puede tener \"feedback_questions\"" 
                          + json_data 
                          + "\nSos un encuestador. A partir de las preguntas recolecta información. Si una pregunta principal tiene "
                          + "\"feedback_questions\" vas a preguntar individualmente, una por una cada pregunta de seguimiento "
                          + "inmediatamente después de su pregunta principal. Si una respuesta a las preguntas principales no te brinda la informacion necesaria, " 
                          + "o la respuesta es muy blanda o vaga (por ejemplo: \"nada\", \"no se\", \"no estoy seguro\", \"bien\", \"mal\", etc), hace tus propias preguntas de seguimiento " 
                          + "y se inquisitivo hasta tener respuestas satisfactorias. "
                          + "Si la respuesta te brinda suficiente informacion, continua con la siguiente pregunta. Solamente enviaras una pregunta en tus mensajes, "
                          + "no vas a insinuar respuestas para que el usuario conteste. Comenza con la primera pregunta."
                          + "En cuanto termines la encuesta, escribi 'LISTO' para finalizar la conversación.")

        send = {"content":selected_questions,
                "hash": hash(chat),
                "response": response.text}
        chats[hash(chat)]=chat
        picMap[hash(chat)] = questionWithPic
        urlMap[hash(chat)] = questionsWithUrl
        startTimes[hash(chat)] = datetime.now()
        return JsonResponse(send)
    return Response({'error': 'Invalid request method'})

@csrf_exempt
def communicate(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        index = request.POST.get('hash')
        response = (chats[int(index)]).send_message(prompt)
        answer = (response.text).replace("\n", "")
        url = None
        pic = None
        urls = urlMap[int(index)]
        pics = picMap[int(index)]
        print(urls)
        print(pics)
        if len(urls) > 0:
            for element in urls:
                if element["question"] == answer:
                    url = element["url"]
                    print(url)
                    break
                
        if len(pics) > 0:
            for element in pics:
                if element["question"] == answer:
                    pic = element["picture"]
                    print(pic)
                    break
                
        if response.text.__contains__('LISTO'):
            chats.pop(int(index))
            urlMap.pop(int(index))
            picMap.pop(int(index))
            
        if url is not None and pic is not None:
            return JsonResponse({'response': answer, 'url': url, 'pic': pic})
        if url is not None:
            return JsonResponse({'response': answer, 'url': url})
        if pic is not None:
            return JsonResponse({'response': answer, 'pic': pic})  
        return JsonResponse({'response': answer})
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt #ahorita no sirve
def logs(request):
    if request.method == 'POST':
        study_id = request.POST['study_id']
        index = request.POST['hash']
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'})
        
        if index is None:
            return JsonResponse({'error': 'Index not provided'})
        
        study = db['Surveys'].find_one({'study_id': ObjectId(study_id)})
        if study is None:
            return JsonResponse({'error': 'Study not found'})
        
        currentChat = chats[int(index)]
        history = currentChat.history
        history = history[1:]
        print(history)
    return JsonResponse({'error': 'Invalid request method'})