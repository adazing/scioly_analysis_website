from django.db import models
from django.contrib.auth.models import User
from datetime import date

# Create your models here.

# 
class Competition(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now=False,auto_now_add=False)
    number_of_teams_competed = models.PositiveIntegerField()
    # average_school_rank = models.FloatField()
    def __str__(self):
        return self.name

# Talking about which events either the A team of B team did for one specific competition.    
class Team(models.Model):
    name = models.CharField(max_length=200)
    competition = models.ForeignKey(Competition, on_delete = models.CASCADE)
    # number_of_teams_competed = models.PositiveIntegerField()
    # score_data = models.FileField(upload_to="scores")
    def __str__(self):
        return self.name
    
# Gets how well a team did on a specific event for a specific competition.
class EventMemberInstance(models.Model):
    # member_1_name = models.CharField(max_length=200)
    event_name = models.CharField(max_length=200)
    team = models.ForeignKey(Team, on_delete = models.CASCADE)
    score = models.PositiveIntegerField()
    def __str__(self):
        return "score of "+str(self.score)+" for "+self.event_name+" for Team "+self.team.name+" for Competition "+self.team.competition.name
    class Meta:
        ordering = ["event_name"]

    # class Meta:
    #     unique_together = ('event_name', 'team')
    
# What members were on the event instance (which members you're actually talking about for event instance) 
class Member(models.Model):
    name = models.CharField(max_length=200)
    event_member_instance = models.ForeignKey(EventMemberInstance, on_delete = models.CASCADE)
    def __str__(self):
        return self.name+" got a score of "+str(self.event_member_instance.score)+" on "+self.event_member_instance.event_name+" for Team "+self.event_member_instance.team.name+" for Competition "+self.event_member_instance.team.competition.name
    class Meta:
        ordering = ["name"]


class Practice(models.Model):
    event_name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now=False,auto_now_add=False)
    total_points = models.FloatField()

class EventMemberPracticeInstance(models.Model):
    practice = models.ForeignKey(Practice, on_delete = models.CASCADE)
    member_name = models.CharField(max_length=200)
    points_scored = models.FloatField()


class SkillData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    experience_rate = models.FloatField(default = 0.1)
    start_date = models.DateField(default = date(date.today().year, 8, 1))
    end_date = models.DateField(default = date(date.today().year + 1, 8, 1))
# class SkillDataVal(models.Model)
# class PracticeMember(models.Model):
#     name = models.CharField(max_length=200)
#     practice_instance = models.ForeignKey(EventMemberPracticeInstance, on_delete = models.CASCADE)
#     def __str__(self):
#         return self.name+" got a practice score of "+str(self.practice_instance.points_scored)+" on "+self.self.practice_instance.practice.event_name+" out of "+str(self.practice_instance.practice.)
#     class Meta:
#         ordering = ["name"]

