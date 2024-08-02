#Login/views.py
from django.utils.html import strip_tags
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from rest_framework.permissions import IsAdminUser
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from anymail.message import AnymailMessage

from .serializers import UserSerializer, UserRegisterSerializer, UserLoginSerializer, PasswordResetRequestSerializer, SetPasswordSerializer, UserEmailSerializer, UpdateUserStatusSerializer 
from .models import User


@api_view(['POST'])
@permission_classes([AllowAny])
def user_register(request):
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        user = User.objects.get(email=serializer.validated_data['email'])
        user.set_password(serializer.validated_data['password1'])
        user.save()
        token = Token.objects.create(user=user)
        return Response({'message': 'Your account has been created and is awaiting approval.',
                         'token': token.key, "user": serializer.data}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(request, email=email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                token, created = Token.objects.get_or_create(user=user)
                return Response({'token': token.key}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Your account is awaiting approval.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    token = request.auth
    if token:
        try:
            token.delete()
        except Token.DoesNotExist:
            pass
        logout(request)
    return Response({'message': 'You have successfully logged out.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()
        if user is not None:
            subject = 'Password Reset Requested'
            email_template_name = 'password_reset_email.html'
            c = {
                'email': user.email,
                'domain': 'localhost:63342/',
                'site_name': 'Los Pixies',
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': default_token_generator.make_token(user),
                'protocol': 'http',
            }
            email_body = render_to_string(email_template_name, c)
            text_content = strip_tags(email_body)
            message = AnymailMessage(
                subject=subject,
                body=text_content,
                from_email= 'cheetahresearch0201@gmail.com',
                to=[user.email],
            )
            message.attach_alternative(email_body, "text/html")
            try:
                message.send()
            except Exception as e:
                return Response({'error': f'Invalid header found: {e}'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'message': 'An email has been sent to you with password reset instructions.'}, status=status.HTTP_200_OK)
        return Response({'error': 'An account with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request, uidb64=None, token=None):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        serializer = SetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['new_password1'] != serializer.validated_data['new_password2']:
                return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password1'])
            user.save()
            return Response({'message': 'Password has been reset.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response({'error': 'The reset password link is no longer valid.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def nonactive_user(request):
    users = User.objects.filter(is_active=False)
    serializer = UserEmailSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def activate_user(request):
    serializer = UpdateUserStatusSerializer(data=request.data)

    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            user.is_active = True
            user.save()
            return Response({'status': 'User activated'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
