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
        response = chat.send_message(prompt + "Este es una encuesta con preguntas, cada pregunta principal \"question\" puede tener \"feedback_questions\"" 
                          + json_data 
                          + "\nSos un encuestador con personalidad " +tone+ ". A partir de las preguntas recolecta información. Si una pregunta principal tiene "
                          + "\"feedback_questions\" vas a preguntar individualmente, una por una cada pregunta de seguimiento "
                          + "inmediatamente después de su pregunta principal. El \"weight\" (1-10) de cada pregunta principal indica la importancia a una respuesta adecuada a esa pregunta."
                          + "Haras las preguntas de forma textual tal y como se te presentan, sin modificar, repetir, eliminar, una pregunta por ningun motivo."
                          + "Tu personalidad no debe influir en cambiar la estructura de una pregunta, es sumamente importante que sigas las instrucciones al pie de la letra. "
                          + "Si una respuesta a las preguntas principales no te brinda la informacion necesaria, " 
                          + "o la respuesta es muy blanda o vaga (por ejemplo: \"nada\", \"no se\", \"no estoy seguro\", \"bien\", \"mal\", etc), hace tus propias preguntas de seguimiento " 
                          + "y se inquisitivo hasta tener respuestas satisfactorias. "
                          + "Si la respuesta te brinda suficiente informacion, continua con la siguiente pregunta. Solamente enviaras una pregunta en tus mensajes, "
                          + "no vas a insinuar respuestas para que el usuario conteste. Comenza con la primera pregunta."
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
        #Get prompt and index from request
        prompt = request.POST.get('prompt')
        index = request.POST.get('hash')
        
        if index is None or prompt is None:
            return JsonResponse({'error': 'Index or prompt not provided'})
        
        #Send message to chatbot
        response = (chats[int(index)]).send_message(prompt)
        answer = (response.text).replace("\n", "")
        
        #Get url and file path from question, if they exist
        url = None
        pic = None
        urls = urlMap[int(index)]
        pics = picMap[int(index)]
        
        if len(urls) > 0:
            for element in urls:
                if element["question"] == answer:
                    url = element["url"]
                    print(url)
                    break
                
        if len(pics) > 0:
            for element in pics:
                if element["question"] == answer:
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
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt #ahorita no sirve
def logs(request):
    """_summary_: This function saves the chatbot conversation log in a csv file.

    Args:
        request (): API request

    Returns:
        JsonResponse: This function returns a JSON response with the message 'Log saved', or an error message.
    """
    
    if request.method == 'POST':
        #Get study_id and index from request
        study_id = request.POST['study_id']
        index = request.POST['hash']
        
        #Check if study_id and index are provided
        if study_id is None:
            return JsonResponse({'error': 'Study ID not provided'})
        
        if index is None:
            return JsonResponse({'error': 'Index not provided'})
        
        #Get study from database
        study = db['Surveys'].find_one({'_id': ObjectId(study_id)})
        if study is None:
            return JsonResponse({'error': 'Study not found'})
        
        #Get chat instance,  questions for history, and start time
        currentChat = chats[int(index)]
        currentQuestions = questionsForHistory[int(index)]
        history = currentChat.history
        history = history[2:]
        
        
        #Save log in csv file
        data = []
        data.append(index)
        
        #Get start time and time taken
        data.append(startTimes[int(index)])
        data.append((datetime.now()-startTimes[int(index)]))
        line = ''
        
        #Get chat history
        for message in history:
            if message.role == 'user':
                line += message.parts[0].text
            if message.role == 'model':
                count = 0
                temp = (message.parts[0].text).replace("\n", "").replace("\r", "").lower()
                for question in currentQuestions:
                    str = question.lower()
                    if str in temp or "listo" in temp:
                        data.append(line)
                        line = ''
                        break
                    else:
                        count += 1
                
                if count == len(currentQuestions):
                    line += ', '

        #Save log in csv file
        csv_key = f"surveys/{study_id}/log_{study_id}.csv"
        if(object_exists(bucket_name, csv_key)):
            # Get the file from S3, if it exists
            csv_obj = s3.get_object(Bucket=bucket_name, Key=csv_key)
            csv_body = csv_obj['Body'].read()
            resultEncoding = chardet.detect(csv_body)
            csv = csv_body.decode(resultEncoding['encoding'])
            df = pd.read_csv(StringIO(csv))
            
            # Create a new row with the new data
            new_df = pd.DataFrame([data],columns=df.columns) 
            
            # Append the new row to the DataFrame
            df = pd.concat([df, new_df], ignore_index=True)
            
            # if the file has enough responses, update the last_update field in the survey_logs collection
            if df.size > 19:
                db['survey_logs'].update_one({'_id': ObjectId(study_id)}, {'$set': {'last_update': datetime.now()}}, upsert=True)

            # Save the updated DataFrame to S3
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            s3.put_object(Bucket=bucket_name, Key=csv_key, Body=csv_buffer.getvalue(), ContentType='text/csv')
        else:
            # The file does not exist, so create it  
            columns = []
            columns.append('index')
            columns.append('start_time')
            columns.append('time_taken')
            for question in currentQuestions:
                columns.append(question)

            df = pd.DataFrame([data],columns=columns)
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            s3.put_object(Bucket=bucket_name, Key=csv_key, Body=csv_buffer.getvalue(), ContentType='text/csv')
                
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
        
    return JsonResponse({'error': 'Invalid request method'})

def object_exists(bucket_name, object_key):
    s3 = boto3.client('s3')
    try:
        s3.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise e