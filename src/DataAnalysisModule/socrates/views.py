from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
import boto3
import chardet
import os
from bson import ObjectId
import json
import pandas as pd
from io import BytesIO

GEMINI_API_KEY = settings.GEMINI_API_KEY
db = settings.MONGO_DB 
s3 = boto3.client('s3', 
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                  region_name='us-east-1')
bucket_name = settings.BUCKET_NAME

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

chats = {}
genaiFiles = {}

@csrf_exempt
def startS(request):
    try:
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
            
            analisis = db['Summaries'].find_one({'_id': ObjectId(study_id)})
            
            if analisis is not None:
                json_data = json.dumps(analisis, indent=4)
                chat.send_message("Te llamas Socrates, se te enviaran uno o mas archivos acerca de un estudio, y un resumen de este estudio."+ json_data+
                            "Tu funcion es analizarlos y contestar preguntas que te hagan sobre el estudio. Puedes extrapolar resultados segun demografia, y otros "+
                            "campos que te pudieran preguntar. Te basaras solamente en los archivos y el resumen para contestar las preguntas."+
                            "Tendras un tono profesional y objetiva, y daras resulados detallados y minuciosos de la pregunta hecha. " +
                            "Puedes sacar estadisticas a partir de los documentos proporcionados, especialmente documentos csv. "+
                            "Seguiras recibiendo archivos hasta que yo te de diga LISTO. Luego contestaras todas las preguntas que se te hagan. ")  
            else:
                chat.send_message("Te llamas Socrates, se te enviaran uno o mas archivos acerca de un estudio."+
                            "Tu funcion es analizarlos y contestar preguntas que te hagan sobre el estudio. Puedes extrapolar resultados segun demografia, y otros "+
                            "campos que te pudieran preguntar. Te basaras solamente en los archivos y el resumen para contestar las preguntas."+
                            "Tendras un tono profesional y objetiva, y daras resulados detallados y minuciosos de la pregunta hecha. " +
                            "Puedes sacar estadisticas a partir de los documentos proporcionados, especialmente documentos csv. "+
                            "Seguiras recibiendo archivos hasta que yo te de diga LISTO. Luego contestaras todas las preguntas que se te hagan. ")  
            
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
                        resultEncoding = chardet.detect_all(csv_body)
                        print(type(resultEncoding))  # This will print the type of resultEncoding
                        csv_content = None
                        if isinstance(resultEncoding, dict):
                            print("resultEncoding is a dictionary")
                            csv_content = csv_body.decode(resultEncoding['encoding'])
                        elif isinstance(resultEncoding, list):
                            print("resultEncoding is a list")
                            print(resultEncoding)
                            csv_content = csv_body.decode((resultEncoding[0])['encoding'])

                        with open(path, 'wb') as f:
                            f.write(csv_content.encode('utf-8'))
                            chatFile = genai.upload_file(path)
                            print(chatFile)
                            filesGenai.append(chatFile)
                            res = chat.send_message([chatFile, "analiza este archivo"])
                    if file_obj["ContentType"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                        file_content = file_obj['Body'].read()

                        # Convert the Excel file content to a Pandas DataFrame
                        excel_data = BytesIO(file_content)
                        df = pd.read_excel(excel_data)
                        name = file_key.split('/')[-1]
                        noExt = name.split('.')[0]
                        path = f"./storage/{noExt}.csv"
                        # Write the DataFrame to a CSV file
                        df.to_csv(path, index=False)
                        
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
    except Exception as e:
        print(e)
        return JsonResponse({'error': 'An error occurred', 'message': e})
    return Response({'error': 'Invalid request method'})

@csrf_exempt
def communicateS(request):
    if request.method == 'POST':
        try:
            #Get the chat from the hashmap
            index = request.POST['hash']
            prompt = request.POST['prompt']
            if index is None or prompt is None:
                return JsonResponse({'error': 'Index or prompt not provided'})
            chat = chats[int(index)]
            response = chat.send_message(prompt)
            return JsonResponse({"response" : response.text})
        except Exception as e:
            print(e)
            return JsonResponse({'error': 'An error occurred', 'message': e})
    return Response({'error': 'Invalid request method'})

@csrf_exempt
def stopS(request):
    if request.method == 'POST':
        try:
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
        except Exception as e:
            print(e)
            return JsonResponse({'error': 'An error occurred', 'message': e})
    return Response({'error': 'Invalid request method'})
    