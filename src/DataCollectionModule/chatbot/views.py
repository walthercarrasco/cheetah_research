from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.response import Response
import google.generativeai as genai
from bson import ObjectId
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import json
import pandas as pd
from io import StringIO
import chardet
from rapidfuzz import fuzz,utils
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import sys

# Get the settings from the settings.py file
GEMINI_API_KEY = settings.GEMINI_API_KEY
db = settings.MONGO_DB 
s3 = boto3.client('s3', 
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
bucket_name = settings.BUCKET_NAME
bucket_url = settings.BUCKET_URL
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-1.5-pro')

chats = {} #dictionary to store chat instances
picMap = {} #dictionary to store questions with pictures
urlMap = {} #dictionary to store questions with urls
questionsForHistory = {} #dictionary to store all questions
startTimes = {} #dictionary to store start times of chats
ids = {}

@csrf_exempt
def start(request):
    """_summary_ : This function starts a chatbot conversation with a user and sends the first question of a survey.

    Args:
        request:  API request

    Returns:
        JsonResponse: This function returns a JSON response with the first question of a survey.
    """
    if request.method == 'POST':
        #Get study_id from request
        study_id = request.POST['study_id']
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'})
        
        #Get study from database
        study = db['Surveys'].find_one({'_id': ObjectId(study_id)})
        if study is None:
            return JsonResponse({'error': 'Study not found'})
        
        #Get interviewer from database
        interviewer = db['Interviewer'].find_one({'_id': ObjectId(study_id)})

        tone = interviewer['interviewerTone']
        
        #Get questions from study
        questions = study['questions']
        
        #Select questions, questions with urls and questions with pictures from study
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
                        "feedback_questions": [fb_question for fb_question in question["feedback_questions"]],
                        "weight": question["weight"]
                    }
                )
            else:
                selected_questions.append(
                    {
                        "question": question["question"],
                        "weight": question["weight"]
                    }
                )
                
            if "file_path" in question:
                questionWithPic.append(
                    {
                        "question": question["question"],
                        "file_path": question["file_path"]
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
        response = chat.send_message("Este es una encuesta con preguntas, cada pregunta principal \"question\" puede tener \"feedback_questions\"" 
                          + json_data 
                          + "\nSos un encuestador con personalidad " +tone+ ". A partir de las preguntas recolecta información. Si una pregunta principal tiene "
                          + "\"feedback_questions\" vas a hacer cada pregunta de seguimiento individualmente inmediatamente despues de su pregunta principal."
                          + "El \"weight\" de cada pregunta principal indica la importancia a una respuesta adecuada a esa pregunta."
                          + "Si una respuesta a las preguntas principales no te brinda la informacion necesaria, " 
                          + "o la respuesta es muy blanda o vaga (por ejemplo: \"nada\", \"no se\", \"no estoy seguro\", \"bien\", \"mal\", etc), realiza pregunas de seguimiento hasa que te quede clara la respuesta " 
                          + "y se inquisitivo hasta tener respuestas satisfactorias. Pregunta acerca del contexto, detalles, ejemplos, o el por qué de la respuesta. "
                          + "Si la respuesta te brinda suficiente informacion, continua con la siguiente pregunta. Solamente enviaras una pregunta en tus mensajes, "
                          + "y nunca vas a insinuar respuestas para que el usuario conteste. " 
                          + "Cada vez que hagas una pregunta principal, vas a enviarlo de la siguiente forma: \"" + study_id + ": (pregunta principal) \"."
                          + "Las \"feedback_questions\" y tus propias preguntas de seguimiento las vas a enviar de forma normal, sin el id de la encuesta."
                          + "Procura tener una conversación fluida y natural, y no te preocupes si no entiendes algo, puedes pedir aclaraciones. "
                          + "Comenzaras con la siguiente pregunta, sin nada agregado de parte tuya, \"Hola, te entrevistaré el día de hoy. Cómo deseas que me dirija hacia ti a lo largo de esta entrevista?\"."
                          + "Luego, en cada pregunta tanto principal como de seguimiento, "
                          + "te vas a dirijir a la persona entrevistada con el nombre que se te proporcione en todas las preguntas principales, y empezaras con la primera pregunta de la encuesta. "
                          + "En cuanto termines la encuesta, escribi solamente 'LISTO' para finalizar la conversación.")
        
        #Send first question to chatbot
        send = {"content":selected_questions,
                "hash": hash(chat),
                "response": (response.text).replace(study_id +':', "").replace('\n', '')}  

        #Store chat instance, questions with pictures, questions with urls, questions for history and start time
        chats[hash(chat)]=chat
        picMap[hash(chat)] = questionWithPic
        urlMap[hash(chat)] = questionsWithUrl
        questionsForHistory[hash(chat)] = allQuestions
        startTimes[hash(chat)] = datetime.now()
        ids[hash(chat)] = study_id
        return JsonResponse(send)
    return Response({'error': 'Invalid request method'})

@csrf_exempt
def communicate(request):
    """_summary_ : This function sends a message to the chatbot and returns the response.

    Args:
        request (_type_): API request

    Returns:
        JsonResponse: This function returns a JSON response with the chatbot response, and the url or file path if the response has one.
    """
    if request.method == 'POST':
        try:
            #Get prompt and index from request
            prompt = request.POST.get('prompt')
            index = request.POST.get('hash')
            study_id = ids[int(index)]
            if index is None or prompt is None:
                return JsonResponse({'error': 'Index or prompt not provided'})
            
            #Send message to chatbot
            try:
                response = (chats[int(index)]).send_message(prompt,
                        safety_settings={
                            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
                        })
                answer = (response.text).replace(study_id +':', "").replace('\n', '')
            except Exception as e:
                print('Failed to send message to chatbot: ')
                print(sys.exc_info())
                return JsonResponse({'error': 'Failed to send message to chatbot'}, status=500)
            
            #Get url and file path from question, if they exist
            url = None
            pic = None
            urls = urlMap[int(index)]
            pics = picMap[int(index)]
            
            if len(urls) > 0:
                for element in urls:
                    accept=fuzz.token_set_ratio(element["question"], answer, processor=utils.default_process)
                    if accept > 80:
                        url = element["url"]
                        print(url)
                        urls.remove(element)
                        break
                    
            if len(pics) > 0:
                for element in pics:
                    accept=fuzz.token_set_ratio(element["question"], answer, processor=utils.default_process)
                    if accept > 80:
                        pic = element["file_path"]
                        print(pic)
                        pics.remove(element)
                        break
                
            #Return response with url or file path
            if url is not None and pic is not None:
                return JsonResponse({'response': answer, 'url': url, 'file_path': pic})
            if url is not None:
                return JsonResponse({'response': answer, 'url': url})
            if pic is not None:
                return JsonResponse({'response': answer, 'file_path': pic})  
            return JsonResponse({'response': answer})
        except Exception as e:
            print('Unknown Error: ' + sys.exc_info())
            return JsonResponse({'error': 'Unknown Error'}, status=500)
    return JsonResponse({'error': 'Invalid request method'},)

@csrf_exempt #ahorita no sirve
def logs(request):
    """_summary_: This function saves the chatbot conversation log in a csv file.

    Args:
        request (): API request

    Returns:
        JsonResponse: This function returns a JSON response with the message 'Log saved', or an error message.
    """
    
    if request.method == 'POST':
        try:
            try:
            #Get study_id and index from request
                study_id = request.POST['study_id']
                index = request.POST['hash']
            except Exception as e:
                return JsonResponse({'error': 'No study_id or index provided'}, status=500)
            #Check if study_id and index are provided
            if study_id is None:
                return JsonResponse({'error': 'Study ID not provided'}, status=500)
            
            if index is None:
                return JsonResponse({'error': 'Index not provided'}, status=500)
            
            #Get study from database
            try:
                study = db['Surveys'].find_one({'_id': ObjectId(study_id)})
            except Exception as e:
                print(e)
                return JsonResponse({'error': 'Failed to access database'}, status=500)
            if study is None:
                return JsonResponse({'error': 'Study not found'}, status=500)
            
            #Get chat instance,  questions for history, and start time
            currentChat = chats[int(index)]
            currentQuestions = questionsForHistory[int(index)]
            history = currentChat.history
            history = history[4:]
            print('History: ')
            
            #Save log in csv file
            data = []
            data.append(index)
            
            #Get start time and time taken
            data.append(startTimes[int(index)])
            data.append((datetime.now()-startTimes[int(index)]))
            line = ''
            
            #Get chat history
            print('Get chat history: ')
            try:
                for message in history:
                    if message.role == 'user':
                        line += message.parts[0].text
                    if message.role == 'model':
                        if study_id in message.parts[0].text:
                            data.append(line)
                            line = ''
                        else:
                            line += ','
                if(line != ''):
                    data.append(line)
                for i in range(len(data)):
                    if(i > 3):
                        print(str(i) + ':' + data[i])
            except Exception as e:
                print('Failed to get chat history in main method: ')
                print(sys.exc_info())
                logs2(request,currentQuestions)
            
            #Save log in csv file
            print('Length Data: ') 
            print(len(data))  
            csv_key = f"surveys/{study_id}/log_{study_id}.csv"
            
            if(object_exists(bucket_name, csv_key)):
                # Get the file from S3, if it exists
                try:
                    print('Get file from S3: ')
                    csv_obj = s3.get_object(Bucket=bucket_name, Key=csv_key)
                except Exception as e:
                    print('Failed to get file from S3: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to get file from S3'})
                
                # Read the csv file
                csv_body = csv_obj['Body'].read()
                resultEncoding = chardet.detect(csv_body)
                csv = csv_body.decode(resultEncoding['encoding'])
                df = pd.read_csv(StringIO(csv))
                
                # Create a new row with the new data
                print('Create new row: ')
                new_df = pd.DataFrame([data],columns=df.columns) 
                
                # Append the new row to the DataFrame
                print('Append new row to DataFrame: ')
                df = pd.concat([df, new_df], ignore_index=True)
                
                # if the file has enough responses, update the last_update field in the survey_logs collection
                if df.size > 10:
                    db['survey_logs'].update_one({'_id': ObjectId(study_id)}, {'$set': {'last_update': datetime.now()}}, upsert=True)

                # Save the updated DataFrame to S3
                print('Save updated DataFrame to S3: ')
                csv_buffer = StringIO()
                
                try:
                    df.to_csv(csv_buffer, index=False)
                except Exception as e:
                    print('Failed to save csv file: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to save csv file'})
                try:
                    s3.put_object(Bucket=bucket_name, Key=csv_key, Body=csv_buffer.getvalue(), ContentType='text/csv')
                except Exception as e:
                    print('Failed to put csv file in S3: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to put csv file in S3 '})
            else:
                # The file does not exist, so create it  
                try:
                    columns = []
                    columns.append('index')
                    columns.append('start_time')
                    columns.append('time_taken')
                    for question in currentQuestions:
                        columns.append(question)
                except Exception as e:
                    print('Failed to create columns: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to create columns'})
                
                df = pd.DataFrame([data],columns=columns)
                
                try:
                    csv_buffer = StringIO()
                    df.to_csv(csv_buffer, index=False)
                except Exception as e:
                    print('Failed to save new csv file: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to save new csv file'})
                
                try:
                    s3.put_object(Bucket=bucket_name, Key=csv_key, Body=csv_buffer.getvalue(), ContentType='text/csv')
                except Exception as e:
                    print('Failed to put new csv file in S3: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to put new csv file in S3'})
                
                #if the study is a test, tag the file to be deleted in 3 days
                if study['test']==True:
                    s3.put_object_tagging(
                        Bucket=bucket_name,
                        Key=csv_key,
                        Tagging={
                            'TagSet': [
                                {
                                    'Key': 'DeleteAfter',
                                    'Value': '3days'
                                }
                            ]
                        }
                    )
            
            #Delete chat instance, questions with pictures, questions with urls, questions for history and start time from dictionaries
            chats.pop(int(index))
            urlMap.pop(int(index))
            picMap.pop(int(index))
            startTimes.pop(int(index))
            questionsForHistory.pop(int(index))
            ids.pop(int(index))
            print('Log saved NORMAL')
            return JsonResponse({'response': 'Log saved'})  
        except Exception as e:
            print('Unknown Error (normal): ')
            print(sys.exc_info())
            logs2(request,currentQuestions)
            return JsonResponse({'error': 'Unknown Error'}, status=500) 
    return JsonResponse({'error': 'Invalid request method'})

#este lo hace gemini
def logs2(request,currentQuestions):
    if request.method == 'POST':
        try:
            try:
            #Get study_id and index from request
                study_id = request.POST['study_id']
                index = request.POST['hash']
            except Exception as e:
                return JsonResponse({'error': 'No study_id or index provided'}, status=500)
            #Check if study_id and index are provided
            if study_id is None:
                return JsonResponse({'error': 'Study ID not provided'}, status=500)
            
            if index is None:
                return JsonResponse({'error': 'Index not provided'}, status=500)
            
            #Get study from database
            try:
                print('get study: ')
                study = db['Surveys'].find_one({'_id': ObjectId(study_id)})
            except Exception as e:
                print(e)
                return JsonResponse({'error': 'Failed to access database'}, status=500)
            if study is None:
                return JsonResponse({'error': 'Study not found'}, status=500)
            
            #Get chat instance,  questions for history, and start time
            currentChat = chats[int(index)]
            history = currentChat.history
            history = history[4:]
            new_history = []
            questions = []
            for message in history:
                new_history.append(
                    {
                        'rol': message.role,
                        'texto': message.parts[0].text
                    }
                )
            for question in currentQuestions:
                questions.append(
                    {
                        'pregunta': question
                    }
                )
                
            send_questions = json.dumps(questions)
            send_history = json.dumps(new_history)
            prompt = """
                    Tu funcion es extraer las respuestas de un usuario a las preguntas de la encuesta.
                    Tendras un historial que tiene 'rol' y 'texto' como llaves, 'rol' puede ser 'user' o 'model' y 'texto' es el mensaje.
                    Tendras una lista que tiene 'pregunta' que son las preguntas principales de una encuesta.
                    En el historial se encuentran las preguntas hechas por el 'model', algunas estan en la lista de preguntas principales y otras no.
                    Debes extraer las respuestas de 'user' a las preguntas principales de la lista de preguntas principales.
                    Si se encuentra una pregunta que no esta en la lista de preguntas principales, debes concatenar la respuesta de 'user' a esa pregunta
                    con la respuesta de la pregunta principal anterior.
                    Las preguntas del model no seran identicas a las preguntas de la lista de preguntas principales, pero estaran identificados con un id 
                    que se te proporcionara. Ocupas identificar las preguntas del model que corresponden a las preguntas principales.
                    
                    Por ejemplo:
                    Preguntas Principales:
                    {
                        "pregunta": "Cual es tu nombre?"
                        "pregunta": "Cual es tu genero?"
                        "pregunta": "Cual es tu edad?"
                    }
                    
                    Historial:
                    {
                        "rol": "model",
                        "texto": "Hola, podrias decirme cual es tu nombre?"
                    },
                    {
                        "rol": "user",
                        "texto": "Juan"
                    },
                    {
                        "rol": "model",
                        "texto": "Gracias, y cual es tu apellido?"
                    },
                    {
                        "rol": "user",
                        "texto": "Dominguez"
                    },
                    {
                        "rol": "model",
                        "texto": "Ahora, cual es tu genero?"
                    },
                    {
                        "rol": "user",
                        "texto": "Masculino"
                    }
                    {
                        "rol": "model",
                        "texto": "Cual es tu edad?"
                    },
                    {
                        "rol": "user",
                        "texto": "20"
                    },
                    {
                        "rol": "model",
                        "texto": "Cual es tu direccion?"
                    },
                    {
                        "rol": "user",
                        "texto": "Calle 5"
                    }
                    
                    Extraer respuestas:
                    "Juan, Dominguez", Masculino, "20, Calle 5"
                    
                    Como ves, Juan y Dominguez se concatenan, y 20 y Calle 5 se concatenan, 
                    porque las preguntas "Cual es tu apellido?" y "Cual es tu genero?" no estan en la lista de preguntas principales, ya que son secundarias.
                    Se concatenan las respuestas de las preguntas principales con las respuestas de las preguntas secundarias.
                    Se pueden concatenar varias preguntas secundarias con preguntas principales
                    
                    Tu salida seria de la siguiente manera:
                    "Juan, Dominguez"
                    Masculino 
                    "20, Calle 5"
                    
                    La cantidad de lineas de tu salida tiene que ser identica a la cantidad de preguntas principales.
                    No envies mensaje propio, solo envia las respuestas de la manera que te lo pido. Comienza con el siguiente historial y lista de preguntas principales:
                    
                    """
            send = 'Historial: ' + send_history + '\n\nPreguntas Principales: ' + send_questions + '\n\nID: ' + study_id
            response = model.generate_content(prompt + send)
            answers = []
            answers.append(index)
            
            #Get start time and time taken
            answers.append(startTimes[int(index)])
            answers.append((datetime.now()-startTimes[int(index)]))
            
            split = response.text.split('\n')
            for element in split:
                if element != '':
                    answers.append(element)
            
            for i in range(len(answers)):
                print(i + ': ' + answers[i])
            print('Data Size: ')
            print(len(answers))
            print(response.text)
            csv_key = f"surveys/{study_id}/log_{study_id}.csv"
            
            if(object_exists(bucket_name, csv_key)):
                # Get the file from S3, if it exists
                try:
                    csv_obj = s3.get_object(Bucket=bucket_name, Key=csv_key)
                except Exception as e:
                    print('Failed to get file from S3: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to get file from S3'})
                
                # Read the csv file
                csv_body = csv_obj['Body'].read()
                resultEncoding = chardet.detect(csv_body)
                csv = csv_body.decode(resultEncoding['encoding'])
                df = pd.read_csv(StringIO(csv))
                
                # Create a new row with the new data
                try:
                    print('Create new row: ')
                    new_df = pd.DataFrame([answers],columns=df.columns) 
                    
                    # Append the new row to the DataFrame
                    print('Append new row to DataFrame: ')
                    df = pd.concat([df, new_df], ignore_index=True)
                except Exception as e:
                    print('Failed to create new row: ')
                    print(sys.exc_info())
                    logstxt(answers, study_id, index)
                    return JsonResponse({'error': 'Failed to create new row'}, status=501)
                # if the file has enough responses, update the last_update field in the survey_logs collection
                if df.size > 10:
                    db['survey_logs'].update_one({'_id': ObjectId(study_id)}, {'$set': {'last_update': datetime.now()}}, upsert=True)

                # Save the updated DataFrame to S3
                csv_buffer = StringIO()
                
                try:
                    df.to_csv(csv_buffer, index=False)
                except Exception as e:
                    print('Failed to save csv file: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to save csv file'})
                try:
                    s3.put_object(Bucket=bucket_name, Key=csv_key, Body=csv_buffer.getvalue(), ContentType='text/csv')
                except Exception as e:
                    print('Failed to put csv file in S3: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to put csv file in S3 '})
            else:
                # The file does not exist, so create it  
                try:
                    columns = []
                    columns.append('index')
                    columns.append('start_time')
                    columns.append('time_taken')
                    for question in currentQuestions:
                        columns.append(question)
                except Exception as e:
                    print('Failed to create columns: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to create columns'})
                
                df = pd.DataFrame([answers],columns=columns)
                
                try:
                    csv_buffer = StringIO()
                    df.to_csv(csv_buffer, index=False)
                except Exception as e:
                    print('Failed to save new csv file: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to save new csv file'})
                
                try:
                    s3.put_object(Bucket=bucket_name, Key=csv_key, Body=csv_buffer.getvalue(), ContentType='text/csv')
                except Exception as e:
                    print('Failed to put new csv file in S3: ')
                    print(sys.exc_info())
                    return JsonResponse({'error': 'Failed to put new csv file in S3'})
                
                #if the study is a test, tag the file to be deleted in 3 days
                if study['test']==True:
                    s3.put_object_tagging(
                        Bucket=bucket_name,
                        Key=csv_key,
                        Tagging={
                            'TagSet': [
                                {
                                    'Key': 'DeleteAfter',
                                    'Value': '3days'
                                }
                            ]
                        }
                    )
            
            #Delete chat instance, questions with pictures, questions with urls, questions for history and start time from dictionaries
            chats.pop(int(index))
            urlMap.pop(int(index))
            picMap.pop(int(index))
            startTimes.pop(int(index))
            questionsForHistory.pop(int(index))
            ids.pop(int(index))
            print('Log saved GEMINI')
            return JsonResponse({'response': 'Log saved'}, status=200)
        except Exception as e:
            print('Failed to get chat history (Gemini): ')
            print(sys.exc_info())
            logstxt(answers, study_id, index)
            return JsonResponse({'error': 'Failed to get chat history'}, status=501)

def object_exists(bucket_name, object_key):
    try:
        s3.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise e
    
@csrf_exempt
def download_logs(request):
    if request.method == 'POST':
        #Get study_id from request
        try:
            study_id = request.POST['study_id']
        except Exception as e:
            return JsonResponse({'error': 'Study ID not provided'}, status=500)
        
        try:
            response = s3.generate_presigned_url('get_object',
                                                        Params={'Bucket': bucket_name, 
                                                                'Key': f"surveys/{study_id}/log_{study_id}.csv"},
                                                        ExpiresIn=1800)  # URL expiration time in seconds (e.g., 1800 seconds = 30 minutes)
            return JsonResponse({'url': response})
        except Exception as e:
            print(e)
            return JsonResponse({'error': 'Failed to download logs'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=500)

@csrf_exempt
def updateLogs(request):
    if request.method == 'POST':
        try:
            #Get study_id and index from request
            study_id = request.POST['study_id']
        except Exception as e:
            return JsonResponse({'error': 'No study_id or index provided'}, status=500)
        #Check if study_id and index are provided
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'}, status=500)
        
        #Erase csv file from S3
        csv_key = f"surveys/{study_id}/log_{study_id}.csv"
        try:
            s3.delete_object(Bucket=bucket_name, Key=csv_key)
        except Exception as e:
            print('Failed to delete csv file: ')
            print(sys.exc_info())
            return JsonResponse({'error': 'Failed to delete csv file'})
        return JsonResponse({'response': 'Log deleted'})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=500)
    

def logstxt(data, study_id, index):
    try:
        txt_key = f"surveys/{study_id}/logbackup_{study_id}.txt"
        new_data = ''
        for element in data:
            new_data += str(element) + ','
        if(object_exists(bucket_name, txt_key)):
            # Get the file from S3, if it exists
            try:
                csv_obj = s3.get_object(Bucket=bucket_name, Key=txt_key)
            except Exception as e:
                print('Failed to get file from S3: ')
                print(sys.exc_info())
                return JsonResponse({'error': 'Failed to get file from S3'})
                    
            # Read the csv file
            txt_body = csv_obj['Body'].read()
            txt = txt_body.decode('utf-8')
            # Create a new row with the new data
            try:
                print('Appending new data to text file: ')
                updated_txt = txt + '\n' + new_data  # Adjust how you append new_data based on format
            except Exception as e:
                print('Failed to append new data: ')
                print(sys.exc_info())
                return JsonResponse({'error': 'Failed to append new data'})
        
            # Check if the file has enough responses, update the last_update field in the survey_logs collection
            if updated_txt.count('\n') > 10:  # Example check: more than 10 lines
                db['survey_logs'].update_one({'_id': ObjectId(study_id)}, {'$set': {'last_update': datetime.now()}}, upsert=True)
            
            # Save the updated text file back to S3
            try:
                s3.put_object(Bucket=bucket_name, Key=txt_key, Body=updated_txt, ContentType='text/csv')
                return JsonResponse({'success': 'Text file updated successfully'})
            except Exception as e:
                print('Failed to put text file in S3: ')
                print(sys.exc_info())
                return JsonResponse({'error': 'Failed to put text file in S3 '})
        else:
            # The file does not exist, so create it
            
            study = db['Surveys'].find_one({'_id': ObjectId(study_id)})    
            try:
                header = 'index,start_time,time_taken,'
                for question in questionsForHistory[int(index)]:
                    header += question + ','
                header = header[:-1]
                new_data = header + '\n' + new_data
                s3.put_object(Bucket=bucket_name, Key=txt_key, Body=new_data, ContentType='text/csv')
            except Exception as e:
                print('Failed to put new csv file in S3: ')
                print(sys.exc_info())
                return JsonResponse({'error': 'Failed to put new csv file in S3'})
                
            #if the study is a test, tag the file to be deleted in 3 days
            if study['test']==True:
                s3.put_object_tagging(
                    Bucket=bucket_name,
                    Key=txt_key,
                    Tagging={
                        'TagSet': [
                            {
                                'Key': 'DeleteAfter',
                                'Value': '3days'
                            }
                        ]
                    }
                )
                
            #Delete chat instance, questions with pictures, questions with urls, questions for history and start time from dictionaries
            chats.pop(int(index))
            urlMap.pop(int(index))
            picMap.pop(int(index))
            startTimes.pop(int(index))
            questionsForHistory.pop(int(index))
            ids.pop(int(index))
            print('Log saved TXT')
    except Exception as e:
        print('Unknown Error (txt): ')
        print(sys.exc_info())
        return JsonResponse({'error': 'Unknown Error'}, status=502)
    
@csrf_exempt
def download_logstxt(request):
    if request.method == 'POST':
        #Get study_id from request
        try:
            study_id = request.POST['study_id']
        except Exception as e:
            return JsonResponse({'error': 'Study ID not provided'}, status=500)
        
        try:
            response = s3.generate_presigned_url('get_object',
                                                        Params={'Bucket': bucket_name, 
                                                                'Key': f"surveys/{study_id}/logbackup_{study_id}.txt"},
                                                        ExpiresIn=1800)  # URL expiration time in seconds (e.g., 1800 seconds = 30 minutes)
            return JsonResponse({'url': response})
        except Exception as e:
            print(e)
            return JsonResponse({'error': 'Failed to download logs'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=500)