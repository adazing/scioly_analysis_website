from django.shortcuts import render
import random
from .models import *
# from .serializers import *
from .forms import *
import string
# import pandas as pd
import csv
from django.http import HttpResponseRedirect
from django.urls import reverse
from formtools.wizard.views import SessionWizardView
import data.models
import copy
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core import serializers
import json
import math
import time
from scipy.optimize import minimize
import numpy as np

# Create your views here.

# print(data.models.Competition)

# TODO: MAKE SURE THAT ONLY ALPHABET LETTERS ARE ALLOWED (NO PUNCTUATION THAT CAN CAUSE XSS ATTACKS)
def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.replace("(B)", "").replace("(3)", "").lower().replace("&", "and") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)", "").lower() if c.isalpha() or c==" "])
    return input_string.strip().title()

def available_events_reader(available_events, generated_competition_settings):
    reader = csv.reader(available_events.splitlines(), delimiter=',')

    for row in reader:
        # print(row)
        event_type=EventType.objects.create(generated_competition_settings=generated_competition_settings)# create() already saves it -- FIX OTHER INSTANCES
        for e in row:
            event_name=remove_punctuation(e, True)
            if event_name!="":
                # print("hi2")
                needs_3_members = "(3)" in e
                is_build_event = "(B)" in e
                # print(event_name)
                AvailableEvent.objects.create(name=event_name, needs_3_members=needs_3_members, generated_competition_settings=generated_competition_settings, event_type=event_type, is_build_event=is_build_event)
            else: # reached end of row
                break

def conflicting_events_reader(conflicting_events, generated_competition_settings):
    reader = csv.reader(conflicting_events.splitlines(), delimiter=',')
    # TODO: CHECK THAT CONFLICTING EVENT EXISTS IN AVAILABLE_EVENTS, SAME FOR MEMBERS IN MEMBER_MEMBER_EVENT_PREFERENCES
    for row in reader:
        conflict = ConflictingEvents.objects.create(generated_competition_settings=generated_competition_settings)
        for e in row:
            event_name=remove_punctuation(e, True)
            # check if event exists
            if event_name!="":
                event_exists = AvailableEvent.objects.filter(name=event_name, generated_competition_settings=generated_competition_settings).exists()
                # print(event_exists)
                # print(AvailableEvent.objects.filter(name=event_name, generated_competition_settings=generated_competition_settings))
                if event_exists:
                    event = AvailableEvent.objects.get(name=event_name, generated_competition_settings=generated_competition_settings)
                    event.conflict = conflict
                    event.save()
            else:
                break

def member_event_preferences_reader(member_event_preferences_data, generated_competition_settings):
    reader = csv.reader(member_event_preferences_data.splitlines(), delimiter=',')
    # next(reader)
    for row in reader:
        # print(row)
        member_name=row[0]
        # print(member_name)
        is_senior = "(S)" in member_name
        member_name=remove_punctuation(member_name, False)
        member = AvailableMember.objects.create(generated_competition_settings=generated_competition_settings, name=member_name, is_senior=is_senior)
        # if len(row)!=1:
        e_idx = 0
        for event in row:
            event_name = remove_punctuation(event, True)
            if event_name!="":
                # is_required = "(*)" in event_name
                event_exists = AvailableEvent.objects.filter(name=event_name, generated_competition_settings=generated_competition_settings).exists()
                if event_exists:
                    e_idx += 1
                    event = AvailableEvent.objects.get(name=event_name, generated_competition_settings=generated_competition_settings)
                    WantedMemberEventPair.objects.create(rank=e_idx, event=event, member=member)
            else: # reached end of row
                break

def member_member_event_preferences_reader(member_member_event_preferences_data, generated_competition_settings):
    # read member_member_event_preferences_data
    reader = csv.reader(member_member_event_preferences_data.splitlines(), delimiter=',')

    # reader = csv.reader(member_member_event_preferences_data.read().decode('UTF-8').split("\r\n"), delimiter=',')
    # next(reader)
    for row in reader:
        # print(row)
        # what if the members aren't actually mentioned before--> just pass that pair and move on
        try:
            member_1_name = remove_punctuation(row[0], False)
            # print("member 1 name",member_1_name)
            member_1 = AvailableMember.objects.get(generated_competition_settings=generated_competition_settings, name=member_1_name)
            member_2_name = remove_punctuation(row[1], False)
            # print("member 2 name",member_2_name)
            member_2 = AvailableMember.objects.get(generated_competition_settings=generated_competition_settings, name=member_2_name)
            event_name = remove_punctuation(row[2], True)
            # print("event name", event_name)
            # print(event_name=="")
            event = AvailableEvent.objects.get(name=event_name, generated_competition_settings=generated_competition_settings) if event_name!="" else None
            if event==None:
                WantedMemberMemberEventPair.objects.create(member1=member_1, member2=member_2)
            else:
                WantedMemberMemberEventPair.objects.create(member1=member_1, member2=member_2, event=event)
            # print(wanted_member_member_event_pair)
        except:
            continue
    # return redirect("generatedCompetitionSettingsView", pk=generated_competition_settings.id)

@login_required
def competitionSettingsFormView(request):
    form = CompetitionSettingsForm(request.POST or None, request.FILES or None)
    # print("hi3")
    if request.method == "POST":
        # print(request.POST)
        # print(form.errors)
        if form.is_valid():
            # print("hi")
            # make initial settings constants
            generated_competition_settings = GeneratedCompetitionSettings.objects.create(user=request.user, name = form.cleaned_data.get("name"), notes = form.cleaned_data.get("notes"), max_events_per_member = form.cleaned_data.get("max_events_per_member"), min_events_per_member = form.cleaned_data.get("min_events_per_member"), skill_vs_preferences = form.cleaned_data.get("skill_vs_preferences"), max_num_of_build_events_per_member=form.cleaned_data.get("max_num_of_build_events_per_member"))
            
            #analyze files
            available_events = form.cleaned_data["available_events"]
            conflicting_events = form.cleaned_data["conflicting_events"] or None
            member_event_preferences_data = form.cleaned_data["member_event_preferences_data"]
            member_member_event_preferences_data = form.cleaned_data["member_member_event_preferences_data"] or None
            
            
            # read available_events
            available_events_reader(available_events, generated_competition_settings)
            
            # read conflicting_events if it exists
            if conflicting_events is not None:
                conflicting_events_reader(conflicting_events, generated_competition_settings)

            # read member_event_preferences_data
            member_event_preferences_reader(member_event_preferences_data, generated_competition_settings)
                    
            # read member_member_event_preferences_data
            if member_member_event_preferences_data is not None:
                member_member_event_preferences_reader(member_member_event_preferences_data, generated_competition_settings)
            
            # finished
            return redirect("generatedCompetitionSettingsView", pk=generated_competition_settings.id)
                    
    context={
        "form":form,
    }
    return render(request, 'generation/settings.html', context)

@login_required
def generatedCompetitionSettingsEdit(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if request.user.id == generated_competition_settings.user.id:
        form = CompetitionSettingsForm(request.POST or None, request.FILES or None, instance=generated_competition_settings)
        # print("hi3")
        if request.method == "POST":
            # print(request.POST)
            # print(form.errors)
            if form.is_valid():
                # print("hi")
                
                # make initial settings constants
                generated_competition_settings.name = form.cleaned_data.get("name")
                generated_competition_settings.notes = form.cleaned_data.get("notes")
                generated_competition_settings.max_events_per_member = form.cleaned_data.get("max_events_per_member")
                generated_competition_settings.min_events_per_member = form.cleaned_data.get("min_events_per_member")
                generated_competition_settings.skill_vs_preferences = form.cleaned_data.get("skill_vs_preferences")
                generated_competition_settings.max_num_of_build_events_per_member = form.cleaned_data.get("max_num_of_build_events_per_member")
                generated_competition_settings.save()
                
                # delete past data
                AvailableEvent.objects.filter(generated_competition_settings = generated_competition_settings).delete()
                AvailableMember.objects.filter(generated_competition_settings = generated_competition_settings).delete()
                EventType.objects.filter(generated_competition_settings = generated_competition_settings).delete()
                ConflictingEvents.objects.filter(generated_competition_settings = generated_competition_settings).delete()

                # print(AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings))

                
                #analyze files
                available_events = form.cleaned_data["available_events"]
                conflicting_events = form.cleaned_data["conflicting_events"] or None
                member_event_preferences_data = form.cleaned_data["member_event_preferences_data"]
                member_member_event_preferences_data = form.cleaned_data["member_member_event_preferences_data"] or None
                
                # read available_events
                available_events_reader(available_events, generated_competition_settings)
                
                # read conflicting_events if it exists
                if conflicting_events is not None:
                    conflicting_events_reader(conflicting_events, generated_competition_settings)

                # read member_event_preferences_data
                member_event_preferences_reader(member_event_preferences_data, generated_competition_settings)
                        
                # read member_member_event_preferences_data
                if member_member_event_preferences_data is not None:
                    member_member_event_preferences_reader(member_member_event_preferences_data, generated_competition_settings)
                
                # print(AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings))
                
                return redirect("generatedCompetitionSettingsView", pk=generated_competition_settings.id)
                        
        context={
            "form":form,
        }
        return render(request, 'generation/settings.html', context)
    raise Http404

@login_required
def generatedCompetitionSettingsView(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    # generated_competition_settings = GeneratedCompetitionSettings.objects.get(id=pk)
    if generated_competition_settings.user.id == request.user.id:
        team_list = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings)
        # final_team_event_pairs = FinalTeamEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings)
        context={
            "generated_competition_settings":generated_competition_settings,
            "team_list":team_list,
        }
        return render(request, "generation/generated_competition_settings_view.html", context)
    raise Http404

@login_required
def generatedTeamCreateView(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if generated_competition_settings.user.id == request.user.id:
        # members_list = AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings)
        # print(members_list)
        # events_list = AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)
        # requirements_list = AvailableMember.objects.filter(generated_competition_settings=generated_team.generated_competition_settings, required_team = generated_team)
        form=TeamForm(request.POST or None)
        if request.method=="POST":
            if form.is_valid():
                GeneratedTeam.objects.create(name=form.cleaned_data.get("name"), notes=form.cleaned_data.get("notes"), generated_competition_settings=generated_competition_settings, team_size=form.cleaned_data.get("team_size"))
                # print(form.cleaned_data.get("required_members"))
                # for m in form.cleaned_data.get("required_members"):
                #     m.required_team = generated_team
                #     m.save()
                    # RequiredMemberToTeam.objects.create(member=m, team = generated_team)
                return redirect('generatedCompetitionSettingsView', pk=generated_competition_settings.id)
        context={
            "form": form,
            # "members_list" : members_list,
            # "events_list" : events_list,
            # "requirements_list": requirements_list,
        }
        return render(request, "generation/team_edit.html", context)
    raise Http404

@login_required
def generatedTeamEditView(request, pk):
    generated_team = get_object_or_404(GeneratedTeam, id=pk)
    
    if generated_team.generated_competition_settings.user.id == request.user.id:
        # list_of_required_members_to_teams = RequiredMemberToTeam.objects.filter(team=generated_team)
        # list_of_required_members_to_teams = AvailableMember.objects.filter(generated_competition_settings=generated_team.generated_competition_settings, required_team = generated_team)
        # preselected_members = [m for m in AvailableMember.objects.filter(generated_competition_settings=generated_team.generated_competition_settings) if list_of_required_members_to_teams]
        # form = TeamForm(request.POST or None, instance=generated_team, initial={'required_members':preselected_members}, queryset=list_of_required_members_to_teams)
        # form = TeamForm(request.POST or None, instance=generated_team, queryset=list_of_required_members_to_teams)
        # members_list = AvailableMember.objects.filter(generated_competition_settings=generated_team.generated_competition_settings)
        # events_list = AvailableEvent.objects.filter(generated_competition_settings=generated_team.generated_competition_settings)
        # requirements_list = AvailableMember.objects.filter(generated_competition_settings=generated_team.generated_competition_settings, required_team = generated_team)
        # print(members_list)
        form = TeamForm(request.POST or None, instance=generated_team)
        print(form.errors)
        if request.method=="POST":
            if form.is_valid():
                generated_team.name=form.cleaned_data.get("name")
                generated_team.notes=form.cleaned_data.get("notes")
                generated_team.team_size=form.cleaned_data.get("team_size")
                generated_team.save()
                # list_of_required_members_to_teams.delete()
                # for m in form.cleaned_data.get("required_members"):
                #     RequiredMemberToTeam.objects.create(member=m, team = generated_team)
                return redirect('generatedCompetitionSettingsView', pk=generated_team.generated_competition_settings.id)
        context={
            # "members_list": members_list,
            # "events_list" : events_list,
            "form":form,
            # "requirements_list": requirements_list,
        }
        return render(request, "generation/team_edit.html", context)
    raise Http404

def editRequirementsView(request, pk):
    generated_team = get_object_or_404(GeneratedTeam, id=pk)
    
    if generated_team.generated_competition_settings.user.id == request.user.id:
        member_queryset = AvailableMember.objects.filter(generated_competition_settings = generated_team.generated_competition_settings)
        # print(list(member_queryset))
        event_queryset = AvailableEvent.objects.filter(generated_competition_settings = generated_team.generated_competition_settings)

        # find all the members required in other teams
        members_required_in_other_teams = []
        all_teams = GeneratedTeam.objects.filter(generated_competition_settings = generated_team.generated_competition_settings)
        for t in all_teams:
            if t != generated_team:
                requirements = RequiredMemberToTeam.objects.filter(team=t)
                for r in requirements:
                    if r.member not in members_required_in_other_teams:
                        members_required_in_other_teams.append(r.member)
        
        hidden_member_queryset = [m.id for m in members_required_in_other_teams]
        
        requirements = RequiredMemberToTeam.objects.filter(team=generated_team)
        required_members = []
        events_to_members = {}
        seniors = []
        for r in requirements:
            if r.member not in required_members:
                required_members.append(r.member)
            if r.member.is_senior and r.member not in seniors:
                seniors.append(r.member)
            if r.event:
                if r.event not in events_to_members:
                    events_to_members[r.event] = [r.member]
                elif r.event in events_to_members:
                    events_to_members[r.event].append(r.member)
        
        # hide events with max amount of ppl on them
        hidden_event_queryset = [e.id for e in events_to_members if len(events_to_members[e]) >= 2+e.needs_3_members]
        
        # hide members who reached their max limit
        for m in required_members:
            events_done_by_member = [e for e in events_to_members if m in events_to_members[e]]
            if len(events_done_by_member) >= generated_team.generated_competition_settings.max_events_per_member:
                hidden_member_queryset.append(m.id)
        # hide seniors if max seniors has been reached
        if len(seniors) >= 7:
            for s in AvailableMember.objects.filter(generated_competition_settings=generated_team.generated_competition_settings, is_senior=True):
                if s not in required_members:
                    hidden_member_queryset.append(s.id)
            
        form = RequirementsForm(request.POST or None, member_queryset=member_queryset, event_queryset=event_queryset, generated_team=generated_team, requirements = requirements, members_required_in_other_teams=members_required_in_other_teams)
        if request.method=="POST":
            if form.is_valid():
                member = form.cleaned_data.get("member")
                event = form.cleaned_data.get("event")
                RequiredMemberToTeam.objects.create(member=member, event=event, team=generated_team)
                return redirect('editRequirementsView', pk=generated_team.id)
        context = {
            "form" : form,
            "hidden_event_queryset" : hidden_event_queryset,
            "hidden_member_queryset" : hidden_member_queryset,
            "requirements_list" : requirements,
            "generated_team" : generated_team,
        }
        return render(request, "generation/team_edit_restrictions.html", context)
    raise Http404

                    
def deleteRequirement(request, pk):
    requirement = get_object_or_404(RequiredMemberToTeam, id=pk)
    if requirement.team.generated_competition_settings.user.id == request.user.id:
        requirement.delete()
        return redirect('editRequirementsView', requirement.team.id)
    raise Http404

@login_required
def generatedCompetitionsListView(request):
    generated_competitions_list = GeneratedCompetitionSettings.objects.filter(user=request.user.id)
    context = {
        "generated_competitions_list":generated_competitions_list,
    }
    return render(request, "generation/generated_competition_list_view.html", context)

@login_required
def generatedCompetitionsDeleteView(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if generated_competition_settings.user.id == request.user.id:
        form = DeleteConfirmationForm(request.POST or None)
        if request.method == "POST":
            if form.is_valid():
                generated_competition_settings.delete()
                return redirect("generatedCompetitionsListView")
        context = {
            "item": "Generated Competition "+generated_competition_settings.name,
            "form":form,
        }
        return render(request, "generation/confirm_delete.html", context)
    raise Http404

@login_required
def generatedTeamDeleteView(request, pk): # TODO: FIX
    team = get_object_or_404(GeneratedTeam, id=pk)
    if team.generated_competition_settings.user.id == request.user.id:
        form = DeleteConfirmationForm(request.POST or None)
        if request.method == "POST":
            if form.is_valid():
                team.delete()
                return redirect("generatedCompetitionSettingsView", pk=team.generated_competition_settings.id)
        context = {
            "item": "team "+team.name,
            "form":form,
        }
        return render(request, "generation/confirm_delete.html", context)
    raise Http404

def frontend_generate(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)

    if generated_competition_settings.user.id != request.user.id:
        raise Http404
    if not data.models.SkillData.objects.filter(user=request.user).exists():
        data.models.SkillData.objects.create(user=request.user)
    skill_data = data.models.SkillData.objects.get(user=request.user)
    competition_list = data.models.Competition.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of competitions
    practice_list = data.models.Practice.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of practice instances
    competition_to_emis = {} # dictionary that maps competitions to dictionary that pairs (event, member) to quartile
    for c in competition_list: # for all the competitions
        emis_list = data.models.EventMemberInstance.objects.filter(team__competition=c) # get all the events
        results_dict = dict()
        for emi in emis_list: # for each of the events
            members = [m.name for m in data.models.Member.objects.filter(event_member_instance = emi)] # get all the members in event
            for m in members: # for each member on the event
                if emi.score < c.number_of_teams_competed: # if the scores is less than the number of teams that competed
                    results_dict[(emi.event_name, m)] = 1-emi.score/c.number_of_teams_competed
        if results_dict:
            competition_to_emis[c] = results_dict
    for p in practice_list:
        emis_list = data.models.EventMemberPracticeInstance.objects.filter(practice=p)
        results_dict = dict()
        for emi in emis_list:
            member = emi.member_name
            results_dict[(p.event_name, member)] = emi.points_scored/p.total_points
        if results_dict:
            competition_to_emis[p] = results_dict
    
    all_list = [c for c in competition_to_emis] # all the competitions that have data
    num_competitions = len(all_list) # number of valid competitions
    no_matches_comps = set()
    def custom_loss(params): # calculates math to minimize
        discovered_experience_rate = abs(params[-2])
        skill_no_exp = abs(params[-1])
        total_loss = 0
        for c1 in range(num_competitions): # comp to leave out
            total_comp_loss = 0
            total_num_repeats = 0
            em_to_exp = dict()
            for c2 in range(num_competitions): # for all other comps
                competition = all_list[c2] # other competition you are looking at
                if c1 != c2: # make sure the comp to leave out isn't equivalent to the other comp
                    for event, member in competition_to_emis[competition]: # for all the scores in the other comp
                        score = competition_to_emis[competition][(event, member)]
                        weight = abs(params[c2]*2) # difficulty weight of competition
                        bias = params[c2]*2+1
                        # update event, member pair prev data
                        if (event, member) in em_to_exp:
                            num_times_member_did_event_previously = len(em_to_exp[(event, member)])+1
                            score -= discovered_experience_rate*(math.log(num_times_member_did_event_previously))
                            score = weight * score + bias
                            em_to_exp[(event, member)].append(score)
                        else:
                            score = weight * score + bias
                            em_to_exp[(event, member)] = [score]
                else: # if it's the competition to leave out, add the score None to people's data
                    for event, member in competition_to_emis[competition]:
                        score = None
                        if (event, member) in em_to_exp:
                            em_to_exp[(event, member)].append(score)
                        else:
                            em_to_exp[(event, member)] = [score]
            no_matches = True # if the comp has no matches with other comps, then not possible so ignore
            for event, member in em_to_exp: # for every event, member pair in em_to_exp data
                if None in em_to_exp[(event, member)]: # the event, member pair participated in left out competition
                    total_num_repeats += 1 
                    left_out_idx = em_to_exp[(event, member)].index(None) # index of left out comp
                    num_other_instances = len(em_to_exp[(event, member)])-1
                    if num_other_instances==0: # no other instances, left out comp is first time doing it
                        pred = skill_no_exp
                    else: # there exists other instances, calculate average of all other past instances
                        no_matches = False
                        pred = 0
                        for i in range(num_other_instances+1):
                            if i != left_out_idx:
                                pred += em_to_exp[(event, member)][i]/num_other_instances
                    weight = abs(params[c1*2]) # difficulty weight of left out comp
                    bias = params[c1*2+1] # bias of left out comp
                    competition = all_list[c1]
                    actual = competition_to_emis[competition][(event, member)] # actual score
                    pred = (pred - bias)/ weight + discovered_experience_rate*(math.log(left_out_idx+1))
                    total_comp_loss += (actual - pred)**2
            if no_matches:
                no_matches_comps.add(c1)
            else:
                total_loss += (total_comp_loss/total_num_repeats)/num_competitions

        return total_loss
    
    class TimeLimitCallback:
        def __init__(self, time_limit):
            self.start_time = time.time()
            self.time_limit = time_limit
            self.best_result = None

        def __call__(self, xk):
            elapsed_time = time.time() - self.start_time
            if elapsed_time >= self.time_limit:
                raise StopIteration("Time limit reached")
            self.best_result = xk
    time_limit = 5 #seconds
    callback = TimeLimitCallback(time_limit)
    try:
        new_params = minimize(custom_loss, np.asarray([0.5 for x in range(num_competitions*2+2)]), options={"disp":False}, callback=callback).x
    except StopIteration:
        new_params = callback.best_result
    # print(new_params)
    # print("experience rate",abs(new_params[-2]))


    # teams that are in generated_competition_settings
    teams = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings)
    available_members = [m.name for m in AvailableMember.objects.filter(generated_competition_settings = generated_competition_settings)]
    available_events = sorted([e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)])
    events_with_3_members = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, needs_3_members=True)]
    build_events = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, is_build_event=True)]
    
    member_event_pairs = [(me.member.name, me.event.name, me.rank) for me in WantedMemberEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings)]

    worst_preference_amount = max([m_e[2] for m_e in member_event_pairs]) if len(member_event_pairs)>0 else 0
    member_member_event_pairs = [[mme.member1.name, mme.member2.name, mme.event.name if mme.event is not None else None] for mme in WantedMemberMemberEventPair.objects.filter(member1__generated_competition_settings=generated_competition_settings)]
    # officers = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, status="O")]
    # senior_members = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, is_senior=True)]
    required_members = []
    required_members_on_events = []
    # teams = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings)
    for t in range(len(teams)):
        requirements = RequiredMemberToTeam.objects.filter(team=teams[t])
        t_required_members = []
        t_required_members_on_events = []
        for r in requirements:
            if r.member.name not in t_required_members:
                t_required_members.append(r.member.name)
            if r.event is not None:
                t_required_members_on_events.append([r.member.name, r.event.name])
        required_members.append(t_required_members)
        required_members_on_events.append(t_required_members_on_events)


    seniors = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, is_senior=True)]
    conflicting_events=[[e.name for e in AvailableEvent.objects.filter(conflict=c, generated_competition_settings=generated_competition_settings)] for c in ConflictingEvents.objects.filter(generated_competition_settings=generated_competition_settings)]
    event_types = [[e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, event_type = et)] for et in EventType.objects.filter(generated_competition_settings=generated_competition_settings)]

    members_to_ranked_preferences = dict()
    # add members with ranked_preferences
    for member, event, rank in member_event_pairs:
        if member in members_to_ranked_preferences:
            members_to_ranked_preferences[member].append((event, rank))
        else:
            members_to_ranked_preferences[member]=[(event, rank)]

    # add members with no ranked preferences
    for m in available_members:
        if m not in members_to_ranked_preferences:
            members_to_ranked_preferences[m]=[]

    # sort members_to_ranked_preferences
    members_to_ranked_preferences = {m:[p[0] for p in sorted(members_to_ranked_preferences[m], key= lambda x:x[1])] for m in members_to_ranked_preferences}
            
    #review previous competition data
    members_to_experience={m:{e:0 for e in available_events} for m in available_members}
    members_to_skill_level={m:{e:0 for e in available_events} for m in available_members}


    valid_weights = [new_params[w*2] for w in range(num_competitions) if w not in no_matches_comps]
    valid_biases = [new_params[2*b+1] for b in range(num_competitions) if b not in no_matches_comps]
    if len(valid_weights) == 0:
        average_weight = 0.5
        average_bias = 0
    else:
        average_weight = sum(valid_weights)/len(valid_weights)
        average_bias = sum(valid_biases)/len(valid_biases)
    for non_valid_comp in no_matches_comps:
        new_params[non_valid_comp*2] = average_weight
        new_params[non_valid_comp*2+1] = average_bias
    # for x in range(num_competitions):
    #     print(all_list[x], new_params[x])
    
    
    discovered_experience_rate = abs(new_params[-2])
    
    # members_to_skill_level = dict()
    # members_to_experience = dict()
    # members_to_data = dict()
    # all_events=set()
    for c_idx in range(num_competitions):
        c = all_list[c_idx]
        if c in competition_list:
            emis_list = data.models.EventMemberInstance.objects.filter(team__competition=c)
            school_scores_of_competition = [x.score for x in data.models.EventMemberInstance.objects.filter(team__competition=c) if x.score<=x.team.competition.number_of_teams_competed]
            if len(school_scores_of_competition) != 0:
                for emi in emis_list:
                    if emi.score < c.number_of_teams_competed:
                        weight = abs(new_params[c_idx*2])
                        bias = new_params[c_idx*2+1]
                        event = emi.event_name
                        members = [m.name for m in data.models.Member.objects.filter(event_member_instance = emi)]
                        
                        for m in members:
                            if m in members_to_experience:
                                if event in members_to_experience[m]:
                                    members_to_experience[m][event] += 1
                                    score = 1-(emi.score/c.number_of_teams_competed)
                                    members_to_skill_level[m][event] += weight * (score - discovered_experience_rate*(math.log(members_to_experience[m][event]))) + bias
        else:
            emis_list = data.models.EventMemberPracticeInstance.objects.filter(practice=c)
            for emi in emis_list:
                weight = abs(new_params[c_idx*2])
                bias = new_params[c_idx*2+1]
                event = emi.practice.event_name
                member = emi.member_name
                
                if member in members_to_experience:
                    if event in members_to_experience[member]:
                        members_to_experience[member][event] += 1
                        score = emi.points_scored/c.total_points
                        members_to_skill_level[member][event] += weight * (score - discovered_experience_rate*(math.log(members_to_experience[member][event]))) + bias
    # print()
    experience_rate = skill_data.experience_rate
    for m in members_to_experience:
        for e in members_to_experience[m]:
            if members_to_experience[m][e]!=0:
                members_to_skill_level[m][e] = (members_to_skill_level[m][e]/members_to_experience[m][e] - average_bias)/ average_weight + experience_rate*(math.log(members_to_experience[m][e]+1))
    # print(members_to_skill_level)
    min_score = min([min([members_to_skill_level[m][e] for e in members_to_skill_level[m] if members_to_experience[m][e]>0], default = 0) for m in members_to_skill_level], default=0)
    max_score = max([max([members_to_skill_level[m][e] for e in members_to_skill_level[m] if members_to_experience[m][e]>0], default = 1) for m in members_to_skill_level], default=1)
    
    # scale members_to_skill_level to be between 0 and 1
    for m in members_to_skill_level:
        for e in available_events:
            if members_to_experience[m][e]==0:
                members_to_skill_level[m][e] = 0
            if max_score - min_score != 0:
                members_to_skill_level[m][e] = (members_to_skill_level[m][e] - min_score) / (max_score - min_score)
            else:
                members_to_skill_level[m][e] = 0
        members_to_skill_level[m]=dict(sorted(members_to_skill_level[m].items(), key=lambda item: item[1], reverse=True))


    context = {
        "id" : pk,
        "required_members_on_events" : required_members_on_events,
        "required_members" : required_members,
        "seniors" : seniors,
        "teams" : [t.team_size for t in teams],
        "team_names" : [t.name for t in teams],
        "members_to_ranked_preferences" : members_to_ranked_preferences,
        "member_member_event_pairs" : json.dumps(member_member_event_pairs),
        "generated_competition_settings" : generated_competition_settings,
        "available_members" : available_members,
        "available_events" : available_events,
        "events_with_3_members" : events_with_3_members,
        "build_events" : build_events,
        "worst_preference_amount" : worst_preference_amount,
        "members_to_skill_level" : members_to_skill_level,
        "members_to_experience" : members_to_experience,
        # "empty_list" : [[], [], []],
        # "build_events" : build_events,
        "conflicting_events" : conflicting_events,
        # "required_member_event_pairs" : required_member_event_pairs,
        "event_types" : event_types,
        "min_score" : min_score,
    }
    return render(request, "generation/generation_frontend.html", context)


# def frontend_generate2(request, pk):
#     generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
#     if generated_competition_settings.user.id == request.user.id:
#         # teams that are in generated_competition_settings
#         teams = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings)
#         available_members = [m.name for m in AvailableMember.objects.filter(generated_competition_settings = generated_competition_settings)]
#         available_events = sorted([e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)])
#         events_with_3_members = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, needs_3_members=True)]
#         build_events = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, is_build_event=True)]
        
#         member_event_pairs = [(me.member.name, me.event.name, me.rank) for me in WantedMemberEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings)]

#         worst_preference_amount = max([m_e[2] for m_e in member_event_pairs]) if len(member_event_pairs)>0 else 0
#         member_member_event_pairs = [[mme.member1.name, mme.member2.name, mme.event.name if mme.event is not None else None] for mme in WantedMemberMemberEventPair.objects.filter(member1__generated_competition_settings=generated_competition_settings)]
#         # officers = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, status="O")]
#         # senior_members = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, is_senior=True)]
#         required_members = []
#         required_members_on_events = []
#         # teams = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings)
#         for t in range(len(teams)):
#             requirements = RequiredMemberToTeam.objects.filter(team=teams[t])
#             t_required_members = []
#             t_required_members_on_events = []
#             for r in requirements:
#                 if r.member.name not in t_required_members:
#                     t_required_members.append(r.member.name)
#                 if r.event is not None:
#                     t_required_members_on_events.append([r.member.name, r.event.name])
#             required_members.append(t_required_members)
#             required_members_on_events.append(t_required_members_on_events)

#         seniors = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, is_senior=True)]
#         conflicting_events=[[e.name for e in AvailableEvent.objects.filter(conflict=c, generated_competition_settings=generated_competition_settings)] for c in ConflictingEvents.objects.filter(generated_competition_settings=generated_competition_settings)]
#         event_types = [[e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, event_type = et)] for et in EventType.objects.filter(generated_competition_settings=generated_competition_settings)]
        
#         members_to_ranked_preferences = dict()
#         # add members with ranked_preferences
#         for member, event, rank in member_event_pairs:
#             if member in members_to_ranked_preferences:
#                 members_to_ranked_preferences[member].append((event, rank))
#             else:
#                 members_to_ranked_preferences[member]=[(event, rank)]
        
#         # add members with no ranked preferences
#         for m in available_members:
#             if m not in members_to_ranked_preferences:
#                 members_to_ranked_preferences[m]=[]

#         # sort members_to_ranked_preferences
#         members_to_ranked_preferences = {m:[p[0] for p in sorted(members_to_ranked_preferences[m], key= lambda x:x[1])] for m in members_to_ranked_preferences}
                
#         #review previous competition data
#         members_to_experience={m:{e:0 for e in available_events} for m in available_members}
#         members_to_skill_level={m:{e:0 for e in available_events} for m in available_members}
                
#         for c in data.models.Competition.objects.filter(user=request.user).order_by('date'):
#             emis_list = data.models.EventMemberInstance.objects.filter(team__competition=c)
#             school_scores_of_competition = [x.score for x in data.models.EventMemberInstance.objects.filter(team__competition=c) if x.score<=x.team.competition.number_of_teams_competed]
#             if len(school_scores_of_competition)>0:
#                 average_score_of_team=sum(school_scores_of_competition)/len(school_scores_of_competition)
#                 competition_difficulty = average_score_of_team/max(1, c.number_of_teams_competed)
#                 for emi in emis_list:
#                     if emi.score <= c.number_of_teams_competed and emi.event_name in available_events: # don't count if disqualified or event_name not in available_events
#                         score = competition_difficulty * (c.number_of_teams_competed - emi.score)/max(1, c.number_of_teams_competed)
#                         event = emi.event_name
#                         members = [m.name for m in data.models.Member.objects.filter(event_member_instance = emi)]
                        
#                         for m in members:
#                             if m in available_members and event in available_events:
#                                 members_to_experience[m][event] += 1
#                                 members_to_skill_level[m][event] += score

#         #shuffle dictionary to ensure randomness if two or more people have skills are the same
#         keys = list(members_to_skill_level.keys())
#         random.shuffle(keys)
#         members_to_skill_level={key:members_to_skill_level[key] for key in keys}
#         members_to_experience={key:members_to_experience[key] for key in keys}

#         # min_total_score = min([sum(members_to_skill_level[m].values()) for m in members_to_skill_level])
        
#         for m in members_to_experience:
#             new_member_to_skill_level = dict()
#             for e in members_to_experience[m]:
#                 if members_to_experience[m][e] != 1: # only did event once in the past, invalid
#                     new_member_to_skill_level[e] = members_to_skill_level[m][e]
#             members_to_skill_level[m] = new_member_to_skill_level
        
#         min_score = min([min(members_to_skill_level[m].values(), default = 0) for m in members_to_skill_level], default=0)
#         max_score = max([max(members_to_skill_level[m].values(), default = 1) for m in members_to_skill_level], default=1)

#         print("min_score", min_score)

#         # scale members_to_skill_level to be between 0 and 1
#         for m in members_to_skill_level:
#             for e in available_events:
#                 if e not in members_to_skill_level[m]:
#                     members_to_skill_level[m][e] = 0
#                 else:
#                     if max_score - min_score != 0:
#                         members_to_skill_level[m][e] = (members_to_skill_level[m][e] - min_score) / (max_score - min_score)
#                     else:
#                         members_to_skill_level[m][e] = 0
#             members_to_skill_level[m]=dict(sorted(members_to_skill_level[m].items(), key=lambda item: item[1], reverse=True))
        
        
#         print(members_to_skill_level)

#         context = {
#             "id" : pk,
#             "required_members_on_events" : required_members_on_events,
#             "required_members" : required_members,
#             "seniors" : seniors,
#             "teams" : [t.team_size for t in teams],
#             "team_names" : [t.name for t in teams],
#             "members_to_ranked_preferences" : members_to_ranked_preferences,
#             "member_member_event_pairs" : json.dumps(member_member_event_pairs),
#             "generated_competition_settings" : generated_competition_settings,
#             "available_members" : available_members,
#             "available_events" : available_events,
#             "events_with_3_members" : events_with_3_members,
#             "build_events" : build_events,
#             "worst_preference_amount" : worst_preference_amount,
#             "members_to_skill_level" : members_to_skill_level,
#             "members_to_experience" : members_to_experience,
#             # "empty_list" : [[], [], []],
#             # "build_events" : build_events,
#             "conflicting_events" : conflicting_events,
#             # "required_member_event_pairs" : required_member_event_pairs,
#             "event_types" : event_types,
#             "min_score" : min_score,
#         }
#         # print(context)
#         return render(request, "generation/generation_frontend.html", context)
#     raise Http404

