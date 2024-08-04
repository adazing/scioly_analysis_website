from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator

# Create your models here.

class GeneratedCompetitionSettings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now=True,auto_now_add=False)
    # number_of_teams = models.PositiveIntegerField()
    name = models.CharField(max_length=200)
    notes = models.CharField(max_length=500, blank=True)
    max_events_per_member = models.PositiveIntegerField()
    min_events_per_member = models.PositiveIntegerField()
    # max_number_of_experimental_people = models.PositiveIntegerField() # rename to number_of_new_members
    min_event_experience = models.PositiveIntegerField()
    skill_vs_preferences = models.FloatField()
    max_num_of_build_events_per_member = models.PositiveIntegerField(default=2)
    #skill vs preference score preferences
    def __str__(self):
        return self.name+str(self.id)

class GeneratedTeam(models.Model):
    name = models.CharField(max_length=200)
    notes = models.CharField(max_length=500, blank=True)
    generated_competition_settings = models.ForeignKey(GeneratedCompetitionSettings, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True,auto_now=False)
    team_size = models.PositiveIntegerField()
    # is_displayed = models.BooleanField(default = True)
    # was_part_of_previous_generation = models.BooleanField(default = False)
    class Meta:
        ordering = ["date"]


# IMPORTANCE_CHOICES = (
#     ("O", "Officer"),
#     ("R", "Required Member"),
#     ("N", "Normal Member"),
# )

# class

    
class EventType(models.Model):
    generated_competition_settings = models.ForeignKey(GeneratedCompetitionSettings, on_delete=models.CASCADE)

class ConflictingEvents(models.Model):
    generated_competition_settings = models.ForeignKey(GeneratedCompetitionSettings, on_delete=models.CASCADE)

class AvailableEvent(models.Model):
    name = models.CharField(max_length=200)
    needs_3_members = models.BooleanField(default=False)
    generated_competition_settings = models.ForeignKey(GeneratedCompetitionSettings, on_delete=models.CASCADE)
    conflict = models.ForeignKey(ConflictingEvents, on_delete=models.SET_NULL, null=True, default=None)
    event_type = models.ForeignKey(EventType, on_delete=models.SET_NULL, null=True)
    is_build_event = models.BooleanField(default=False)
    def __str__(self):
        return self.name

class AvailableMember(models.Model):
    generated_competition_settings = models.ForeignKey(GeneratedCompetitionSettings, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    # is_officer = models.BooleanField(default = False)
    # status = models.CharField(max_length=10, choices=IMPORTANCE_CHOICES, default="N")
    # grade_level = models.PositiveIntegerField()
    # required_team = models.ForeignKey(GeneratedTeam, on_delete=models.SET_NULL, null=True)
    # required_event = models.ForeignKey(AvailableEvent, on_delete=models.SET_NULL, null=True)
    # final_team = models.ForeignKey(GeneratedTeam, on_delete=models.SET_NULL, null=True)
    is_senior = models.BooleanField(default = False)
    def __str__(self):
        is_senior=" (senior)" if self.is_senior else ""
        # is_officer = " (officer)" if self.is_officer else ""
        return self.name+is_senior+" "+str(self.generated_competition_settings)

class WantedMemberEventPair(models.Model):
    rank = models.PositiveIntegerField()
    event = models.ForeignKey(AvailableEvent, on_delete=models.CASCADE)
    member = models.ForeignKey(AvailableMember, on_delete=models.CASCADE)
    # required = models.BooleanField(default=False)
    def __str__(self):
        return "("+str(self.rank)+") "+self.event.name+" "+self.member.name

# class RequiredMemberEventPair(models.Model):
#     event = models.ForeignKey(AvailableEvent, on_delete=models.CASCADE)
#     member = models.ForeignKey(AvailableMember, on_delete=models.CASCADE)
    

class WantedMemberMemberEventPair(models.Model):
    member1 = models.ForeignKey(AvailableMember, on_delete=models.CASCADE, related_name="member1")
    member2 = models.ForeignKey(AvailableMember, on_delete=models.CASCADE, related_name="member2")
    event = models.ForeignKey(AvailableEvent, on_delete=models.CASCADE, null=True)

class RequiredMemberToTeam(models.Model):
    member = models.ForeignKey(AvailableMember, on_delete = models.CASCADE)
    team = models.ForeignKey(GeneratedTeam, on_delete=models.CASCADE)
    event = models.ForeignKey(AvailableEvent, on_delete=models.CASCADE, null=True)


# final generated classes

# class FinalTeamEventPair(models.Model):
#     event = models.ForeignKey(AvailableEvent, on_delete=models.CASCADE)
#     member = models.ForeignKey(AvailableMember, on_delete=models.CASCADE)
#     is_wanted = models.BooleanField()