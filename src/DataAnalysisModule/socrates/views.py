from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
import boto3
import chardet
import os

GEMINI_API_KEY = settings.GEMINI_API_KEY
db = settings.MONGO_DB 
s3 = boto3.client('s3', 
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
bucket_name = settings.BUCKET_NAME

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

chats = {}
genaiFiles = {}

@csrf_exempt
def startS(request):
    if request.method == 'POST':
        #Get study_id from request
        study_id = request.POST['study_id']
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'})
        
        
        #Get all files from the study_id folder
        folder = f"surveys/{study_id}/"
        objects = s3.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=folder)
        
        #Configure Socrates
        chat = model.start_chat(history=[])
        
        chat.send_message("Te llamas Socrates, tu funcion es contestar cualquier pregunta que yo te haga. "+
                          "Te enviare uno o mas archivos, y a partir de esos archivos, tendras que analizarlos "+
                          "para contestar mis preguntas. No contestes preguntas a partir de informacion fuera de "+
                          "esos archivos, solamente te basaras en esos archivos para contestar mis preguntas. " +
                          "Contesta de manera profesional y objetiva, analizando completamente los archivos proporcionados "+
                          "Seguiras recibiendo archivos hasta que yo te de diga LISTO. Tomaras "+
                          "en cuenta todos los archivos para contestar las preguntas. "+
                          "Cuando yo diga LISTO, vas a saludar de la siguiente forma: "+
                          "Hola, soy Socrates, estoy listo para contestar tus preguntas.")  
        
        #Extract the files  
        if 'Contents' in objects:
            files = [item['Key'] for item in objects['Contents'] if item['Key'] != folder]
            filesGenai = []
            
            #Download the files and send them to Socrates
            for file_key in files:
                path = f"./storage/{file_key.split('/')[-1]}"
                if os.path.exists(f"./storage") == False:
                    os.mkdir(f"./storage")
                file_obj = s3.get_object(Bucket=bucket_name, Key=file_key)
                if file_obj["ContentType"] == "application/pdf":
                    s3.download_file(bucket_name, file_key, path)
                    chatFile = genai.upload_file(path)
                    filesGenai.append(chatFile)
                    res = chat.send_message([chatFile])
                    
                if file_obj["ContentType"] == "text/csv":
                    csv_body = file_obj['Body'].read()
                    resultEncoding = chardet.detect(csv_body)
                    csv_content = csv_body.decode(resultEncoding['encoding'])
                    with open(path, 'wb') as f:
                        f.write(csv_content.encode('utf-8'))
                        chatFile = genai.upload_file(path)
                        filesGenai.append(chatFile)
                        res = chat.send_message([chatFile])
                print(res.text)
                os.remove(path)
        
        #Send the Ready message to Socrates
        response = chat.send_message("LISTO")
        chats[hash(chat)] = chat
        genaiFiles[hash(chat)] = filesGenai
        return JsonResponse({"response" : response.text,
                             "hash" : hash(chat)})
    return Response({'error': 'Invalid request method'})

@csrf_exempt
def communicateS(request):
    if request.method == 'POST':
        #Get the chat from the hashmap
        index = request.POST['hash']
        prompt = request.POST['prompt']
        if index is None or prompt is None:
            return JsonResponse({'error': 'Index or prompt not provided'})
        chat = chats[int(index)]
        response = chat.send_message(prompt)
        return JsonResponse({"response" : response.text})
    return Response({'error': 'Invalid request method'})

@csrf_exempt
def stopS(request):
    if request.method == 'POST':
        #Get the chat from the hashmap
        index = request.POST['hash']
        if index is None:
            return JsonResponse({'error': 'Index not provided'})
        
        #End the chat and delete the files
        chats.pop(int(index))
        files = genaiFiles[int(index)]
        for f in files:
            genai.delete_file(f)
        genaiFiles.pop(int(index))
        return JsonResponse({"response" : "Success"})
    return Response({'error': 'Invalid request method'})
    