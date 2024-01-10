from django.urls import path, re_path
from . import views

urlpatterns = [
    path('competition-settings/', views.competitionSettingsFormView, name="competitionSettingsFormView"),
    path('generation-competition/<str:pk>/', views.generatedCompetitionSettingsView, name="generatedCompetitionSettingsView"),
    path('generated-team-settings/<str:pk>/', views.generatedTeamCreateView, name="generatedTeamCreateView"),
    path('generated-team-edit/<str:pk>/', views.generatedTeamEditView, name="generatedTeamEditView"),
    path("generated-competition-edit/<str:pk>/", views.generatedCompetitionSettingsEdit, name="generatedCompetitionSettingsEdit"),
    path('', views.generatedCompetitionsListView, name='generatedCompetitionsListView'),
    path('generated-competititons-delete-view/<str:pk>/', views.generatedCompetitionsDeleteView, name='generatedCompetitionsDeleteView'),
    path('generated-team-delete-view/<str:pk>/', views.generatedTeamDeleteView, name='generatedTeamDeleteView'),
    path('start-real-generation/<str:pk>/', views.generateTeams, name="generateTeams"),
    path('generated-competition/<str:pk>/', views.finalGeneratedCompetitionView, name="finalGeneratedCompetitionView"),
    path('blah/<str:pk>/', views.frontend_generate, name="frontedGenerate"),
    # when edit final generated competition, it causes the generatedCompetitionView to be deleted! Fixed
    # all required members shown when generating teams - fixed
    # make sure conflicting events data has at least 2 events per row
]