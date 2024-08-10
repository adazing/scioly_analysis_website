from django.shortcuts import render

from django.contrib.auth.forms import *
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth import views as auth_views
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordChangeForm, DeleteConfirmationForm
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your views here.

def home(request):
    return render(request, "users/home.html")

def privacyPolicy(request):
    return render(request, 'users/privacy_policy.html')

def termsOfService(request):
    return render(request, "users/terms_of_service.html")

def disclaimers(request):
    return render(request, "users/disclaimers.html")

def signupView(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/signup.html', {'form': form})

def loginView(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # Change 'home' to your desired redirect URL
    else:
        form = CustomAuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

@login_required
def logoutView(request):
    logout(request)
    return render(request, 'users/logout.html')

@login_required
def passwordChangeView(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep the user logged in
            return render(request, 'users/password_change_done.html')
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'users/password_change.html', {'form': form})

@login_required
def deleteAccountView(request):
    form = DeleteConfirmationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = request.user
            user.delete()
            return redirect('home')
    context = {
        "form":form,
    }
    return render(request, 'users/delete_account.html', context)
