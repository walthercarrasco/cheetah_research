from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from bson import ObjectId
from google.cloud import storage
import json
import threading

db = settings.MONGO_DB 
bucket = storage.Client().get_bucket('bucket_cheetah')

@csrf_exempt
def create_question(request, study_id):
    if request.method == 'POST':
        try:
            questions = json.loads(request.POST.get('questions'))
            files = request.FILES.items()
            saveQuestions(questions, study_id, files)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'fail', 'message': str(e)})
    else:
        return JsonResponse({'status': 'fail', 'message': 'Invalid method'})

def saveQuestions(questions, study_id, files):
    # Procesar y almacenar las preguntas en la base de datos
    file_tasks = []
    for key, value in files:
        filename = f"img/{study_id}/{key}.{value.name.split('.')[-1]}"
        questions[int(key) - 1]['file_path'] = filename
        # Crear un hilo para cargar el archivo
        file_task = threading.Thread(target=upload_file_to_bucket, args=(filename, value))
        file_tasks.append(file_task)
        file_task.start()
    
    # Guardar las preguntas en la base de datos
    db['Surveys'].update_one({'study_id': ObjectId(study_id)}, {'$push': {'questions': {'$each': questions}}})

def upload_file_to_bucket(filename, file):
    blob = bucket.blob(filename)
    blob.upload_from_file(file)
