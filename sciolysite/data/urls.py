from django.urls import path, re_path
from . import views

urlpatterns = [
    path('practice/<str:pk>/', views.practiceView, name="practiceView"),
    path('practice-create/', views.practiceCreateView, name="practiceCreateView"),
    path('practice-edit/<str:pk>/', views.practiceEditView, name="practiceEditView"),
    path('practice-delete/<str:pk>/', views.practiceDeleteView, name="practiceDeleteView"),
    path('competition/<str:pk>/', views.competitionView, name="competitionView"),
    path('competition-create/', views.competitionCreateView, name="competitionCreateView"),
    path('competition-edit/<str:pk>/', views.competitionEditView, name="competitionEditView"),
    path('competition-delete/<str:pk>/', views.competitionDeleteView, name="competitionDeleteView"),
    path('team/<str:pk>/', views.teamView, name="teamView"),
    path('team-create/<str:pk>/', views.teamCreateView, name="teamCreateView"),
    path('team-delete/<str:pk>/', views.teamDeleteView, name="teamDeleteView"),
    path('team-edit-results/<str:pk>/', views.editTeamResultsView, name="editTeamResultsView"),
    path('delete-event-result/<str:pk>/', views.deleteEventMemberInstance, name="deleteEventMemberInstance"),
    path('practice-edit-results/<str:pk>/', views.editPracticeResultsView, name="editPracticeResultsView"),
    path('delete-practice-result/<str:pk>/', views.deletePracticeResult, name="deletePracticeResult"),
    path('', views.competitionListView, name="competitionListView"),
    path('skills/', views.skillView2, name="skillView"),
    # path('test-skills/', views.skillView, name="skillView2"),
    path('name-change/', views.nameChange, name="nameChange"),
]