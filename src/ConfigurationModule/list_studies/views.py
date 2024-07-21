from django.conf import settings
from django.http import JsonResponse
from django.conf import settings
from django.http import JsonResponse
from django.conf import settings
from bson.objectid import ObjectId
import google.generativeai as genai

GEMINI_API_KEY = settings.GEMINI_API_KEY
DB = settings.MONGO_DB

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')
chat = model.start_chat()

# Create your views here.
def get_studies(request):
    try:
        data = DB['Study'].find()
        studies = []
        for d in data:
            survey = DB['Surveys'].find_one({'study_id': d.get('_id')})
            if survey:
                prompt = survey.get('prompt')
                questions = survey.get('questions', [])
                print(prompt, questions)
                summary = str(getSummary(prompt, questions).text)
                d['summary'] = summary
            d['_id'] = str(d['_id'])
            studies.append(d)
        print(studies)
        return JsonResponse(studies, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def getSummary(prompt, questions):
    return chat.send_message(f"""
                        Haz un resumen pequeño sobre que trata el siguiente prompt y las siguientes preguntas(puede no haber preguntas):
                        Prompt: {prompt}
                        Questions: {str(questions)} 
                      """)
    
        