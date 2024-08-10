from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('privacy-policy/', views.privacyPolicy, name="privacyPolicy"),
    path('signup/', views.signupView, name='signupView'),
    path('login/', views.loginView, name='loginView'),
    path('logout/', views.logoutView, name='logoutView'),
    path('password-change/', views.passwordChangeView, name='passwordChangeView'),
    path('delete-account/', views.deleteAccountView, name='deleteAccountView'),
    path('terms-of-use/', views.termsOfService, name="termsOfService"),
    path('disclaimers/', views.disclaimers, name="disclaimers"),
]
