#forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, SetPasswordForm
from .models import User

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Email'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Contraseña'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Confirmar contraseña '}))
    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match. Please try again.')

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User

class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Contraseña'}))

    class Meta:
        model = User
        fields = ['username', 'password']

    def clean_username(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email does not exist.")

        user = User.objects.filter(email=email).first()
        if user and not user.is_active:
            raise forms.ValidationError("Your account is awaiting approval.")

        return email

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Email'}))

    class Meta:
        fields = ['email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email does not exist.")
        return email

class SetPasswordForm2(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'New password'}),
    )
    new_password2 = forms.CharField(
        label="New password confirmation",
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Confirm new password'}),
    )

    class Meta:
        model = User
        fields = ['new_password1', 'new_password2']