from django.shortcuts import render

# Create your views here.

def home(request):
    return render(request, "users/home.html")

def privacyPolicy(request):
    return render(request, 'users/privacy_policy.html')