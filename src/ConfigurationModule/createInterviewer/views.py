from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import boto3
from bson import ObjectId
db = settings.MONGO_DB
s3 = boto3.client('s3', 
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
bucket_name = settings.BUCKET_NAME
bucket_url = settings.BUCKET_URL

@csrf_exempt
def createInterviewer(request):
    if request.method == 'POST':
        body = request.POST
        filename = None
        if(request.FILES):
            image_file = request.FILES['interviewerProfilePicture']
            extension = image_file.name.split('.')[-1]
            filename = body.get('study_id') + '.' + extension
            content_type = {
                    "jpeg": "image/jpeg",
                    "jpg": "image/jpeg",
                    "png": "image/png",
            }.get(extension, "application/octet-stream")
            s3.put_object(Bucket='cheetahresearch', Key='pfp/'+filename, Body=image_file, ContentType=content_type)
            s3.put_object_acl(ACL='public-read', Bucket=bucket_name, Key='pfp/'+filename)
            
        data = {
            '_id':ObjectId(body.get('study_id')),
            'interviewerName':body.get('interviewerName'),
            'interviewerProfilePicture':'pfp/'+filename,
            'interviewerTone':body.get('interviewerTone'),
            'interviewerGreeting':body.get('interviewerGreeting'),
            'importantObservation':body.get('importantObservation')
        }
        post = db['Interviewer'].insert_one(data)
        
        return JsonResponse({
            'status': 'success',
            'interviewer_id': str(post.inserted_id)
        })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def getInterviewer(request):
    if request.method == 'POST':
        interviewer = db['Interviewer'].find_one({'_id': ObjectId(request.POST.get('study_id'))})
        pfp = interviewer.get('interviewerProfilePicture')
        return JsonResponse({
                    'interviewer_id': str(interviewer['_id']),
                    'interviewerName': interviewer['interviewerName'],
                    'interviewerProfilePicture': bucket_url + pfp,
                    'interviewerTone': interviewer['interviewerTone'],
                    'interviewerGreeting': interviewer['interviewerGreeting'],
                    '_id': str(interviewer['_id'])
                })
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def updateInterviewer(request):
    if request.method == 'POST':
        try:
            data = request.POST
            interviewer_id = data.get('_id')
            updates = {}

            if 'interviewerProfilePicture' in data:
                interviewer = db['Interviewer'].find_one({'_id': ObjectId(interviewer_id)})
                pfp = interviewer.get('interviewerProfilePicture')
                image_file = request.FILES['interviewerProfilePicture']
                extension = image_file.name.split('.')[-1]
                filename = interviewer_id + '.' + extension
                content_type = {
                    "jpeg": "image/jpeg",
                    "jpg": "image/jpeg",
                    "png": "image/png",
                }.get(extension, "application/octet-stream")
                s3.delete_object(Bucket = bucket_name, Key=pfp)
                s3.put_object(Bucket=bucket_name, Key='pfp/'+filename, Body=image_file, ContentType=content_type)
                s3.put_object_acl(ACL='public-read', Bucket=bucket_name, Key='pfp/'+filename)
                updates['interviewerProfilePicture'] = 'pfp/'+filename
                
            if 'interviewerName' in data:
                updates['interviewerName'] = data['interviewerName']
            if 'interviewerTone' in data:
                updates['interviewerTone'] = data['interviewerTone']
            if 'interviewerGreeting' in data:
                updates['interviewerGreeting'] = data['interviewerGreeting']
            
            if updates:
                result = db['Interviewer'].update_one(
                    {'_id': ObjectId(interviewer_id)},
                    {'set': updates}
                )
                if result.modified_count > 0:
                    return JsonResponse({'status': 'success', 'message': 'Interviewer updated successfully'})
                else:
                    return JsonResponse({'status': 'failure', 'message': 'No changes made or invalid interviewer ID'})
            else:
                return JsonResponse({'status': 'failure', 'message': 'No valid fields to update'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'error': 'Invalid request method'})