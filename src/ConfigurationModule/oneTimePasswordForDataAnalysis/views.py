from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import OTP
from django.utils import timezone

@api_view(['POST'])
@permission_classes([AllowAny])
def generate_otp(request):
    mongo_dbstudio_id = request.data.get('mongo_dbstudio_id')
    if not mongo_dbstudio_id:
        return Response({'error': 'mongo_dbstudio_id is required'}, status=400)

    otp_instance = OTP.generate_otp(mongo_dbstudio_id)
    return Response({'otp': otp_instance.otp, 'expires_at': otp_instance.expires_at})

@api_view(['POST'])
@permission_classes([AllowAny])
def validate_otp(request):
    otp_value = request.data.get('otp')
    mongo_dbstudio_id = request.data.get('mongo_dbstudio_id')

    if not otp_value or not mongo_dbstudio_id:
        return Response({'error': 'OTP and mongo_dbstudio_id are required'}, status=400)

    try:
        otp_instance = OTP.objects.get(otp=otp_value, mongo_dbstudio_id=mongo_dbstudio_id)
        if otp_instance.is_valid():
            otp_instance.mark_as_used()
            return Response({'status': 'success', 'message': 'OTP is valid'})
        else:
            return Response({'status': 'error', 'message': 'OTP is invalid or expired'}, status=400)
    except OTP.DoesNotExist:
        return Response({'status': 'error', 'message': 'Invalid OTP or Studio'}, status=400)