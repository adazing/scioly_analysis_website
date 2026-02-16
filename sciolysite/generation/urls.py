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
    # path('start-real-generation/<str:pk>/', views.generateTeams, name="generateTeams"),
    # path('generated-competition/<str:pk>/', views.finalGeneratedCompetitionView, name="finalGeneratedCompetitionView"),
    path('generate/<str:pk>/', views.frontend_generate, name="frontedGenerate"),
    path('edit-requirements/<str:pk>/', views.editRequirementsView, name="editRequirementsView"),
    path('delete-requirement/<str:pk>/', views.deleteRequirement, name="deleteRequirement"),
    # Edit pages
    path('edit-events/<str:pk>/', views.editEventsView, name="editEventsView"),
    path('delete-event/<str:pk>/', views.deleteEvent, name="deleteEvent"),
    path('delete-event-type/<str:pk>/', views.deleteEventType, name="deleteEventType"),
    path('edit-preferences/<str:pk>/', views.editPreferencesView, name="editPreferencesView"),
    path('delete-preference/<str:pk>/', views.deletePreference, name="deletePreference"),
    path('delete-member/<str:pk>/', views.deleteMember, name="deleteMember"),
    path('edit-partner-preferences/<str:pk>/', views.editPartnerPreferencesView, name="editPartnerPreferencesView"),
    path('delete-partner-preference/<str:pk>/', views.deletePartnerPreference, name="deletePartnerPreference"),
    path('edit-conflicts/<str:pk>/', views.editConflictsView, name="editConflictsView"),
    path('remove-event-from-conflict/<str:pk>/', views.removeEventFromConflict, name="removeEventFromConflict"),
    path('delete-conflict-group/<str:pk>/', views.deleteConflictGroup, name="deleteConflictGroup"),
]