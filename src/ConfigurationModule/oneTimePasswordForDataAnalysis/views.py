from bson import ObjectId
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from .models import OTP
from django.conf import settings
from django.utils import timezone
DB = settings.MONGO_DB
@api_view(['POST'])
@permission_classes([AllowAny])
def generate_otp(request):
    mongo_studio_id = request.data.get('mongo_studio_id')
    if not mongo_studio_id:
        return Response({'error': 'mongo_studio_id is required'}, status=400)

    try:
        DB['Study'].find_one({'_id': ObjectId(mongo_studio_id)})
    except Exception as e:
        return Response({'error': 'Invalid mongo_studio_id'}, status=400)

    existing_otp = OTP.objects.filter(mongo_studio_id=mongo_studio_id)
    if existing_otp.exists():
        existing_otp.delete()
    otp_instance = OTP.generate_otp(mongo_studio_id)
    return Response({'otp': otp_instance.otp, 'expires_at': otp_instance.expires_at})

@api_view(['POST'])
@permission_classes([AllowAny])
def validate_otp(request):
    otp_value = request.data.get('otp')
    mongo_studio_id = request.data.get('mongo_studio_id')

    if not otp_value or not mongo_studio_id:
        return Response({'error': 'OTP and mongo_studio_id are required'}, status=400)

    try:
        otp_instance = OTP.objects.get(otp=otp_value, mongo_studio_id=mongo_studio_id)
        if otp_instance.is_valid():
            otp_instance.mark_as_used()
            return Response({'status': 'success', 'message': 'OTP is valid'})
        else:
            return Response({'status': 'error', 'message': 'OTP is invalid or expired'}, status=400)
    except OTP.DoesNotExist:
        return Response({'status': 'error', 'message': 'Invalid OTP or Studio'}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def get_otp(request):
    mongo_studio_id = request.data.get('mongo_studio_id')
    if not mongo_studio_id:
        return Response({'error': 'mongo_studio_id is required'}, status=400)
    try:
        DB['Study'].find_one({'_id': ObjectId(mongo_studio_id)})
    except Exception as e:
        return Response({'error': 'Invalid mongo_studio_id'}, status=400)
    otp_instance = OTP.objects.filter(mongo_studio_id=mongo_studio_id).first()
    if otp_instance:

        return Response({
            'otp': otp_instance.otp,
            'expires_at': otp_instance.expires_at,
            'used': otp_instance.used
        })
    else:
        return Response({'error': 'No valid OTP found for this studio'}, status=404)

