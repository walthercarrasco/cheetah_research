from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from anymail.message import AnymailMessage
from django.utils.html import strip_tags

from .models import User

from .forms import UserRegisterForm, UserLoginForm, PasswordResetRequestForm, SetPasswordForm2
def user_register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            messages.info(request, 'Your account has been created and is awaiting approval.')
            return redirect('user_login')
        else:
            messages.error(request, 'There was an error creating your account.')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request,  data=request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(email=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, 'You have successfully logged in.')
                    return redirect('home')
                else:
                    messages.error(request, 'Your account is awaiting approval.')
            else:
                messages.error(request, 'Invalid credentials.')




    else:
        form = UserLoginForm()
    return render(request, 'registration/login.html', {'form': form})

def user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have successfully logged out.')
        return redirect('user_login')
    else:
        return render(request, 'base.html')

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email).first()
            if user is not None:
                subject = 'Password Reset Requested'
                email_template_name = 'registration/password_reset_email.html'

                c = {
                    'email': user.email,
                    'domain': get_current_site(request).domain,
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
                print(email_body)
                try:
                    message.send()
                except Exception as e:
                    print(e)
                    return HttpResponse(f'Invalid header found: {e}')
                messages.success(request, 'An email has been sent to you with password reset instructions.')
                return render(request, 'registration/forgot-password.html', {'form': form})
    else:
        form = PasswordResetRequestForm()
    return render(request, 'registration/forgot-password.html', {'form': form})

def password_reset_confirm(request, uidb64=None, token=None):
    try:
        uid= force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm2(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Password has been reset.')
                return redirect('user_login')
        else:
            form = SetPasswordForm2(user)
        return render(request, 'registration/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, 'The reset password link is no longer valid.')
        return redirect('user_login')




@login_required
def home(request):
    return render(request, 'home.html')
