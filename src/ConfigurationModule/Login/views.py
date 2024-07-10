from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from .models import User
from .forms import UserRegisterForm, UserLoginForm
def user_register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            #notify admin for validation
            send_mail(
                'New User Registration',
                'A new user has registered. Please validate.',
                settings.DEFAULT_FROM_EMAIL,
                [admin.email for admin in User.objects.filter(is_superuser=True)],
            )
            messages.info(request, 'Your account has been created and is awaiting approval.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(email=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('home')
                else:
                    messages.error(request, 'Your account is awaiting approval.')
            else:
                messages.error(request, 'Invalid credentials.')
    else:
        form = UserLoginForm()
    return render(request, 'login.html', {'form': form})

@login_required
def home(request):
    return render(request, 'home.html')
