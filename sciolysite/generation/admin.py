from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(GeneratedCompetitionSettings)
admin.site.register(GeneratedTeam)
admin.site.register(AvailableMember)
admin.site.register(EventType)
admin.site.register(ConflictingEvents)
admin.site.register(AvailableEvent)
admin.site.register(WantedMemberEventPair)
admin.site.register(WantedMemberMemberEventPair)
# admin.site.register(FinalTeamEventPair)
admin.site.register(RequiredMemberToTeam)