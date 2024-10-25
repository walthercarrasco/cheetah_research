from django.conf import settings
from django.http import JsonResponse
from django.conf import settings
from django.http import JsonResponse
from django.conf import settings
from bson.objectid import ObjectId

DB = settings.MONGO_DB

# Create your views here.
def get_studies(request):
    try:
        data = DB['Study'].find()
        studies = []
        for d in data:
            survey = DB['Surveys'].find_one({'_id': d.get('_id')})
            if survey:
                prompt = survey.get('prompt')
                d['prompt'] = prompt
            d['_id'] = str(d['_id'])
            studies.append(d)
        return JsonResponse(studies, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
        