from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import urllib.request
from bson import ObjectId
import json
import pymongo
import boto3

db = settings.MONGO_DB
@csrf_exempt
def delete_study(request):
    if request.method == 'DELETE':
        print("DELETE")
        try:

            data = json.loads(request.body)
            study_id = data.get('study_id')

            if not study_id or not ObjectId.is_valid(study_id):
                return JsonResponse({'status': 'error', 'message': 'Invalid study'}, status=400)

            study = db['Study'].find_one({'_id': ObjectId(study_id)})
            if not study:
                return JsonResponse({'status': 'error', 'message': 'Study not found.'}, status=404)

            s3 = boto3.client('s3',
                                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                region_name='us-east-1')
            bucket_name = settings.BUCKET_NAME
            bucket_name2 = settings.BUCKET_DATA
            s3_key_prefixprofile = f"pfp/{study_id}"
            s3_key_prefiximagesd = f"images/{study_id}"
            s3_key_prefixanalysis = f"analysis/{study_id}"
            s3_key_prefixsurveys = f"surveys/{study_id}"
            responseprofile = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_key_prefixprofile)
            responseimages = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_key_prefiximagesd)
            responseanalysis = s3.list_objects_v2(Bucket=bucket_name2, Prefix=s3_key_prefixanalysis)
            responsesurveys = s3.list_objects_v2(Bucket=bucket_name2, Prefix=s3_key_prefixsurveys)
            #elimina las imagenes de los perfiles en interviewer
            if 'Contents' in responseprofile:
                for obj in responseprofile['Contents']:
                    s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
            #elimina las imagenes del S3
            if 'Contents' in responseimages:
                for obj in responseimages['Contents']:
                    s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
            #elimina los archivos de analisis
            if 'Contents' in responseanalysis:
                for obj in responseanalysis['Contents']:
                    s3.delete_object(Bucket=bucket_name2, Key=obj['Key'])
            #elimina los archivos de encuestas
            if 'Contents' in responsesurveys:
                for obj in responsesurveys['Contents']:
                    s3.delete_object(Bucket=bucket_name2, Key=obj['Key'])




            db['Study'].delete_one({'_id': ObjectId(study_id)})

            db['Surveys'].delete_many({'_id': ObjectId(study_id)})
            db['Interviewer'].delete_many({'_id': ObjectId(study_id)})
            db['Summaries'].delete_many({'_id': ObjectId(study_id)})
            db['survey_logs'].delete_many({'_id': ObjectId(study_id)})
            db['Surveys'].delete_many({'_id': ObjectId(study_id)})

            return JsonResponse({'status': 'success', 'message': 'Study deleted.'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except pymongo.errors.PyMongoError:
            return JsonResponse({'status': 'error', 'message': 'Database error'}, status=500)

    else :
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
