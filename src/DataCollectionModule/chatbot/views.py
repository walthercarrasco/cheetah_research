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
                          + "\"feedback_questions\" vas a hacer cada pregunta de seguimiento individualmente inmediatamente despues de su preugnta principal."
                          + "El \"weight\" de cada pregunta principal indica la importancia a una respuesta adecuada a esa pregunta."
                          + "Comenzaras con la siguiente pregunta, sin nada agregado de parte tuya, \"Hola, te entrevistaré el día de hoy. Cómo deseas que me dirija hacia ti a lo largo de esta entrevista?\"."
                          + "Te vas a dirijir a la persona entrevistada con el nombre que te de, y empezaras con la primera pregunta de la encuesta. "
                          + "Cuando hagas una pregunta de la encuesta, vas a enviarlo de la siguiente forma: \"(nombre del entrevistado), (pregunta) \". "
                          + "Las preguntas que yo te proporciono ocupas hacerlas justo como yo te las envie, nunca vas a cambiar su estructura, ni una palabra, ni un caracter, absolutamente nada de mis preguntas vas a poder cambiar"
                          + "Tu personalidad no debe influir en cambiar la estructura de una pregunta, es sumamente importante que sigas las instrucciones al pie de la letra. "
                          + "Si una respuesta a las preguntas principales no te brinda la informacion necesaria, " 
                          + "o la respuesta es muy blanda o vaga (por ejemplo: \"nada\", \"no se\", \"no estoy seguro\", \"bien\", \"mal\", etc), hace tus propias preguntas de seguimiento " 
                          + "y se inquisitivo hasta tener respuestas satisfactorias. "
                          + "Si la respuesta te brinda suficiente informacion, continua con la siguiente pregunta. Solamente enviaras una pregunta en tus mensajes, "
                          + "y no vas a insinuar respuestas para que el usuario conteste. "
                          + "En cuanto termines la encuesta, escribi 'LISTO' para finalizar la conversación.")
        
        #Send first question to chatbot
        send = {"content":selected_questions,
                "hash": hash(chat),
                "response": (response.text).replace("\n", "")}
        url = None
        filepath = None
        first = allQuestions[0]
        for element in questionWithPic:
            if element["question"] == first:
                filepath = element["file_path"]
                break
            
        for element in questionsWithUrl:
            if element["question"] == first:
                url = element["url"]
                break
            
        if url is not None and filepath is not None:
            send = {"content":selected_questions,
                    "hash": hash(chat),
                    "response": (response.text).replace("\n", ""),
                    "url": url,
                    "file_path": filepath}
            
        if url is not None:
            send = {"content":selected_questions,
                    "hash": hash(chat),
                    "response": (response.text).replace("\n", ""),
                    "url": url}
            
        if filepath is not None:
            send = {"content":selected_questions,
                    "hash": hash(chat),
                    "response": (response.text).replace("\n", ""),
                    "file_path": filepath}
        
        #Store chat instance, questions with pictures, questions with urls, questions for history and start time
        chats[hash(chat)]=chat
        picMap[hash(chat)] = questionWithPic
        urlMap[hash(chat)] = questionsWithUrl
        questionsForHistory[hash(chat)] = allQuestions
        startTimes[hash(chat)] = datetime.now()

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
                answer = (response.text).replace("\n", "")
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
                        break
                    
            if len(pics) > 0:
                for element in pics:
                    accept=fuzz.token_set_ratio(element["question"], answer, processor=utils.default_process)
                    if accept > 80:
                        pic = element["file_path"]
                        print(pic)
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
                print('get study: ')
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
                        count = 0
                        temp = (message.parts[0].text).replace("\n", "").replace("\r", "").lower()
                        for question in currentQuestions:
                            qlower = question.lower()
                            accept=fuzz.token_set_ratio(temp, qlower, processor=utils.default_process)
                            if (accept > 80) or 'listo' in temp:
                                print(str(currentQuestions.index(question)) + qlower + '=' + str(accept))
                                data.append(line)
                                line = ''
                                currentQuestions.remove(question)
                                break
                            else:
                                count += 1

                        if count == len(currentQuestions):
                            line += ', '
            except Exception as e:
                print('Failed to get chat history: ')
                print(sys.exc_info())
                return JsonResponse({'error': 'Failed to get chat history'})
            
            #Save log in csv file
            print('Save log in csv file: ') 
            print(data.count)  
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
                print('Read csv file: ')
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
                if df.size > 19:
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
            
            return JsonResponse({'response': 'Log saved'})  
        except Exception as e:
            print('Unknown Error: ')
            print(sys.exc_info())
            return JsonResponse({'error': 'Unknown Error'})  
    return JsonResponse({'error': 'Invalid request method'})

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