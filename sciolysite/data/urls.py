from django.urls import path, re_path
from . import views

urlpatterns = [
    path('competition/<str:pk>/', views.competitionView, name="competitionView"),
    path('competition-create/', views.competitionCreateView, name="competitionCreateView"),
    path('competition-edit/<str:pk>/', views.competitionEditView, name="competitionEditView"),
    path('competition-delete/<str:pk>/', views.competitionDeleteView, name="competitionDeleteView"),
    path('team/<str:pk>/', views.teamView, name="teamView"),
    path('team-create/<str:pk>/', views.teamCreateView, name="teamCreateView"),
    path('team-delete/<str:pk>/', views.teamDeleteView, name="teamDeleteView"),
    path('', views.competitionListView, name="competitionListView"),
    path('skills/', views.skillView, name="skillView"),
]