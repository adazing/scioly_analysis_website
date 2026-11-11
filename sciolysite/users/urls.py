from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('privacy-policy/', views.privacyPolicy, name="privacyPolicy"),
    path('signup/', views.signupView, name='signupView'),
    path('login/', views.loginView, name='loginView'),
    path('logout/', views.logoutView, name='logoutView'),
    path('password-change/', views.passwordChangeView, name='passwordChangeView'),
    path('email/', views.emailChangeView, name='emailChangeView'),
    path('password-reset/', views.passwordResetView, name='password_reset'),
    path('password-reset/sent/', views.passwordResetDoneView, name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.passwordResetConfirmView, name='password_reset_confirm'),
    path('password-reset/complete/', views.passwordResetCompleteView, name='password_reset_complete'),
    path('delete-account/', views.deleteAccountView, name='deleteAccountView'),
    path('terms-of-use/', views.termsOfService, name="termsOfService"),
    path('disclaimers/', views.disclaimers, name="disclaimers"),
    path('algorithm/', views.algorithm, name="algorithm"),
]
