from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import google.generativeai as genai
from google.cloud import storage


GEMINI_API_KEY = settings.GEMINI_API_KEY
db = settings.MONGO_DB 

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-1.5-flash')
chat = model.start_chat(history=[])

@csrf_exempt
def start(request):
    if request.method == 'POST':
        interviewer = db['Study'].find_one({'study_id': request.POST['studyId']})
        return JsonResponse({'response': response.text})
    return JsonResponse({'error': 'Invalid request method'})
def communicate(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        response = chat.send_message(prompt)
        return JsonResponse({'response': response.text})
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def logs(request):
    if request.method == 'POST':
        response = chat.send_message('Devuelve el historial de la conversación, a partir de las preguntas principales.'+
                                     'Devuelve las respuestas de las preguntas principales, sin incluir las preguntas de seguimiento.'+
                                     'Concatena todas las respuestas del usuario a su debido pregunta principal'+
                                     'No devuelvas las preguntas de seguimiento')
        return JsonResponse({'response': response.text})
    return JsonResponse({'error': 'Invalid request method'})
# Create your views here.
