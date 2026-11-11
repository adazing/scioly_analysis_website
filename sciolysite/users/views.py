from django.shortcuts import render

from django.contrib.auth.forms import *
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth import views as auth_views
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .forms import CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordChangeForm, DeleteConfirmationForm, EmailChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()

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
    if request.method == "POST":
        logout(request)
        return render(request, 'users/logout.html')
    return redirect('home')

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

def algorithm(request):
    return render(request, "users/algorithm.html")

@login_required
def emailChangeView(request):
    saved = False
    if request.method == 'POST':
        form = EmailChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            saved = True
            form = EmailChangeForm(request.user)
    else:
        form = EmailChangeForm(request.user)
    return render(request, 'users/email_change.html', {'form': form, 'saved': saved})


# Password reset uses Django's built-in, well-tested views. Notes:
# - The form never reveals whether an email is registered.
# - Tokens are single-use (they change once the password changes) and expire
#   after settings.PASSWORD_RESET_TIMEOUT.
# - Links are built from settings.SITE_URL, not the request Host header.
class PasswordResetView(auth_views.PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.txt'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        self.extra_email_context = {'site_url': settings.SITE_URL}
        return super().form_valid(form)

passwordResetView = PasswordResetView.as_view()
passwordResetDoneView = auth_views.PasswordResetDoneView.as_view(
    template_name='users/password_reset_done.html',
)
passwordResetConfirmView = auth_views.PasswordResetConfirmView.as_view(
    template_name='users/password_reset_confirm.html',
    success_url=reverse_lazy('password_reset_complete'),
)
passwordResetCompleteView = auth_views.PasswordResetCompleteView.as_view(
    template_name='users/password_reset_complete.html',
)
