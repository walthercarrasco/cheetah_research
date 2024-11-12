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
str_file = ""

@csrf_exempt
def startS(request):
    if request.method == 'POST':
        #Get study_id from request
        try:
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
            message = """
                    Hola Sócrates,

                    A continuación, se te enviarán uno o más archivos que contienen datos de un estudio. Tu tarea es analizarlos y responder a las preguntas que se te hagan sobre dichos datos. Baserás tus respuestas únicamente en la información contenida en los archivos y en otros datos proporcionados. Mantendrás un tono profesional y objetivo en todas tus respuestas.

                    Tus responsabilidades incluyen:

                    Analizar minuciosamente los archivos proporcionados para identificar toda la información relevante, tópicos que se repiten y tendencias.
                    Identificar y extraer tópicos clave dentro del estudio para una mejor comprensión del contenido.
                    Clasificar y organizar las respuestas, proporcionando un panorama general y detallado de los datos.
                    Resaltar y enfatizar los puntos más importantes y los hallazgos clave que surjan del análisis.
                    Escribir resúmenes concisos pero informativos que cubran los puntos clave del estudio, empezando con una breve introducción que proporcione contexto y describa la importancia del tema, seguido de una presentación clara y estructurada de los puntos principales, utilizando viñetas o listas numeradas para mayor claridad si corresponde.
                    Incluir datos críticos, estadísticas o citas de fuentes autorizadas para agregar credibilidad.
                    Directrices Específicas:

                    OBLIGATORIO: No contabilizar ni mencionar el número de tuplas de los archivos proporcionados en tus respuestas. Concéntrate únicamente en la información y datos relevantes.
                    OBLIGATORIO: Asegúrate de que la suma total de cualquier conjunto de porcentajes sea del 100% al citar porcentajes en tus respuestas.
                    Proceso de trabajo:

                    Continuaré enviándote archivos hasta que te indique "LISTO".
                    Una vez que todos los archivos hayan sido recibidos, estarás preparado para responder todas las preguntas que se te hagan sobre el estudio de manera precisa, detallada y profesional.
                    Gracias por tu colaboración, Sócrates.
                    
                    """

            
            analisis = db['Summaries'].find_one({'_id': ObjectId(study_id)})
            
            if analisis is not None:
                analisis = dict(list(analisis.items())[1:])
                json_data = json.dumps(analisis, indent=4)
                chat.send_message(message + json_data)  
            else:
                chat.send_message(message)     
            #Extract the files  
            filesGenai = []
            if 'Contents' in objects:
                files = [item['Key'] for item in objects['Contents'] if item['Key'] != folder]
                
                #Download the files and send them to Socrates
                for file_key in files:
                    path = f"./storage/{file_key.split('/')[-1]}"
                    if os.path.exists(f"./storage") == False:
                        os.mkdir(f"./storage")
                    file_obj = s3.get_object(Bucket=bucket_name, Key=file_key)
                    if file_obj["ContentType"] == "application/pdf":
                        s3.download_file(bucket_name, file_key, path)
                        chatFile = genai.upload_file(path=path, mime_type="application/pdf")
                        print(chatFile)
                        filesGenai.append(chatFile)
                        res = chat.send_message([chatFile, "Espera al mensaje LISTO, no analices nada aún"])

                    try:
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
                                chatFile = genai.upload_file(path, mime_type="text/csv")
                                print(chatFile)
                                filesGenai.append(chatFile)
                                res = chat.send_message([chatFile, "Espera al mensaje LISTO, no analices nada aún"])
                    except Exception as e:
                        with open(path, 'r') as f:
                            csv_content = f.read()
                            contenido = "ARCHIVO CSV: \n\n\n" + csv_content
                            res = chat.send_message("Espera al mensaje LISTO, no analices nada aún \n\n\n" + contenido)

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
                        
                        chatFile = genai.upload_file(path, mime_type="text/csv")
                        filesGenai.append(chatFile)
                        res = chat.send_message([chatFile, "Espera al mensaje LISTO, no analices nada aún"])
                        print(res.text)
                    os.remove(path)
            
            #Send the Ready message to Socrates
            response = chat.send_message("LISTO")
            chats[hash(chat)] = chat
            if(len(filesGenai) > 0):
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
    
