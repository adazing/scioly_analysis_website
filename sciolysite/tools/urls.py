from django.urls import path, re_path
from . import views

urlpatterns = [
    path('conflict-checking/', views.ConflictCheckingView, name="ConflictCheckingView"),

]