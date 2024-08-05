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


# Create your views here.

# print(data.models.Competition)

# TODO: MAKE SURE THAT ONLY ALPHABET LETTERS ARE ALLOWED (NO PUNCTUATION THAT CAN CAUSE XSS ATTACKS)
def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.replace("(B)","").lower().replace("trial", "").replace("&", "and").replace("(3)","").replace("(*)","") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)","").replace("(O)","").replace("(R)","").lower() if c.isalpha() or c==" "])
    return input_string.strip().title()

def available_events_reader(available_events, generated_competition_settings):
    reader = csv.reader(available_events.splitlines(), delimiter=',')

    for row in reader:
        print(row)
        event_type=EventType.objects.create(generated_competition_settings=generated_competition_settings)# create() already saves it -- FIX OTHER INSTANCES
        for e in row:
            event_name=remove_punctuation(e, True)
            if event_name!="":
                print("hi2")
                needs_3_members = "(3)" in e
                is_build_event = "(B)" in e
                print(event_name)
                event = AvailableEvent.objects.create(name=event_name, needs_3_members=needs_3_members, generated_competition_settings=generated_competition_settings, event_type=event_type, is_build_event=is_build_event)
            else: # reached end of row
                break

def conflicting_events_reader(conflicting_events, generated_competition_settings):
    reader = csv.reader(conflicting_events.splitlines(), delimiter=',')

    for row in reader:
        conflict = ConflictingEvents.objects.create(generated_competition_settings=generated_competition_settings)
        for e in row:
            if e.strip()!="":
                event_name=remove_punctuation(e, True)
                event = AvailableEvent.objects.get(name=event_name, generated_competition_settings=generated_competition_settings)
                event.conflict = conflict
                event.save()
            else:
                break

def member_event_preferences_reader(member_event_preferences_data, generated_competition_settings):
    reader = csv.reader(member_event_preferences_data.splitlines(), delimiter=',')
    # next(reader)
    for row in reader:
        print(row)
        member_name=row[0]
        is_senior = "(S)" in member_name
        member_name=remove_punctuation(member_name, False)
        member = AvailableMember.objects.create(generated_competition_settings=generated_competition_settings, name=member_name, is_senior=is_senior)
        if len(row)!=1:
            event_name=remove_punctuation(row[1], True)
            for e in range(1,len(row)):
                if row[e].strip()!="":
                    event_name = row[e]
                    # is_required = "(*)" in event_name
                    event_name = remove_punctuation(event_name, True)
                    print(event_name)
                    #print(AvailableEvent.objects.all)
                    event = AvailableEvent.objects.get(name=event_name, generated_competition_settings=generated_competition_settings)
                    WantedMemberEventPair.objects.create(rank=e, event=event, member=member)
                else: # reached end of row
                    break

def member_member_event_preferences_reader(member_member_event_preferences_data, generated_competition_settings):
    # read member_member_event_preferences_data
    if member_member_event_preferences_data != None:
        reader = csv.reader(member_member_event_preferences_data.splitlines(), delimiter=',')

        # reader = csv.reader(member_member_event_preferences_data.read().decode('UTF-8').split("\r\n"), delimiter=',')
        next(reader)
        for row in reader:
            print(row)
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
    return redirect("generatedCompetitionSettingsView", pk=generated_competition_settings.id)

@login_required
def competitionSettingsFormView(request):
    form = CompetitionSettingsForm(request.POST or None, request.FILES or None)
    print("hi3")
    if request.method == "POST":
        # print(request.POST)
        print(form.errors)
        if form.is_valid():
            print("hi")
            # make initial settings constants
            generated_competition_settings = GeneratedCompetitionSettings.objects.create(user=request.user, name = form.cleaned_data.get("name"), notes = form.cleaned_data.get("notes"), max_events_per_member = form.cleaned_data.get("max_events_per_member"), min_events_per_member = form.cleaned_data.get("min_events_per_member"), skill_vs_preferences = form.cleaned_data.get("skill_vs_preferences"), min_event_experience=form.cleaned_data.get("min_event_experience"), max_num_of_build_events_per_member=form.cleaned_data.get("max_num_of_build_events_per_member"))
            
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
        print("hi3")
        if request.method == "POST":
            # print(request.POST)
            print(form.errors)
            if form.is_valid():
                print("hi")
                
                # make initial settings constants
                generated_competition_settings.name = form.cleaned_data.get("name")
                generated_competition_settings.notes = form.cleaned_data.get("notes")
                generated_competition_settings.max_events_per_member = form.cleaned_data.get("max_events_per_member")
                generated_competition_settings.min_events_per_member = form.cleaned_data.get("min_events_per_member")
                generated_competition_settings.skill_vs_preferences = form.cleaned_data.get("skill_vs_preferences")
                generated_competition_settings.min_event_experience = form.cleaned_data.get("min_event_experience")
                generated_competition_settings.max_num_of_build_events_per_member = form.cleaned_data.get("max_num_of_build_events_per_member")
                generated_competition_settings.save()
                
                # delete past data
                AvailableEvent.objects.filter(generated_competition_settings = generated_competition_settings).delete()
                AvailableMember.objects.filter(generated_competition_settings = generated_competition_settings).delete()
                EventType.objects.filter(generated_competition_settings = generated_competition_settings).delete()
                ConflictingEvents.objects.filter(generated_competition_settings = generated_competition_settings).delete()
                
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
        members_list = AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings)
        print(members_list)
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
        for r in requirements:
            if r.member not in required_members:
                required_members.append(r.member)
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


def is_valid_team_addition(event, member, team, generated_team, generated_competition_settings, events_with_3_members, build_events):
    events_done_by_member=[e for e in team if member in team[e]]
    members_on_team=set([m for e in team for m in team[e]])
    conflicting_events=[[e.name for e in AvailableEvent.objects.filter(conflict=c, generated_competition_settings=generated_competition_settings)] for c in ConflictingEvents.objects.filter(generated_competition_settings=generated_competition_settings)]
    # print(team)
    #already enough events for the member
    if len(events_done_by_member)>=generated_competition_settings.max_events_per_member:
        # print(1)
        return False
    
    #member already in the event
    elif member in team[event]:
        # print(2)
        return False
    
    #already enough members in the event
    elif len(team[event])>=2+int(event in events_with_3_members):
        # print(3)
        return False
    
    #member has already reached max build events already
    elif len([e for e in events_done_by_member if e in build_events])>=generated_competition_settings.max_num_of_build_events_per_member:
        # print(4)
        return False
    
    #new member would cause the team to go over the size limit
    elif len(members_on_team)+1>generated_team.team_size and member not in members_on_team:
        # print(5)
        return False
    
    #adding member to event would cause conflicts
    conflicts=[0 for e in conflicting_events]
    events_done_by_member.append(event)
    for e in events_done_by_member:
        for c in range(len(conflicting_events)):
            if e in conflicting_events[c]:
                conflicts[c]+=1
        if any([c>=2 for c in conflicts]):
            # print(6)
            return False
    return True


def make_team(available_events, team_members, members_to_ranked_preferences, member_member_event_pairs, generated_team, generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience, build_events):
    best_team = {event: [] for event in available_events}
    best_score = float('inf')
    
    while True:
        team = copy.deepcopy(best_team)
        changed = False
        for event in available_events:
            for member in team_members:
                # print(available_events)
                # print(team_members)
                # print(member, event)
                if is_valid_team_addition(event, member, team, generated_team, generated_competition_settings, events_with_3_members, build_events):
                    # print("is valid")
                    new_team = copy.deepcopy(team)
                    new_team[event].append(member)
                    new_score = calculate_preferences_score(new_team, team_members, members_to_ranked_preferences, member_member_event_pairs, generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience)
                    if new_score < best_score:
                        changed = True
                        best_score = new_score
                        best_team = copy.deepcopy(new_team)
        # print(changed)
        print(best_team)
        if not changed:
            return best_team


def calculate_preferences_score(team, team_members, members_to_ranked_preferences, member_member_event_pairs, generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience):
    
    # goal: get lowest total_preference_score
    
    # extra penalties
    empty_spots = [2-len(team[e])+int(e in events_with_3_members) for e in team]
    # print(empty_spots)
    required_member_event_preferences_not_yet_fulfilled = [me for me in WantedMemberEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings, required = True) if me.member.name not in team[me.event.name]]
    
    # counters
    total_preference_score = 0
    total_skill_score = 0


    for e in team:
        # member-member-event preferences
        for mme in member_member_event_pairs:
            if mme.event is None or mme.event.name==e:
                # if both m1 and m2 in event
                if {mme.member1.name, mme.member2.name} <= set(team[e]):
                    total_preference_score-=worst_preference_amount
                #           there is empty space for the event                      one of the members is in the event                         both members are part of the team                                              both members want to do the event
                elif len(team[e])<2+int(e in events_with_3_members) and (mme.member1.name in team[e] or mme.member2.name in team[e]) and {mme.member1.name, mme.member2.name}<=set(team_members) and (len(WantedMemberEventPair.objects.filter(member=mme.member1, event=AvailableEvent.objects.get(name=e, generated_competition_settings=generated_competition_settings)))!=0 and len(WantedMemberEventPair.objects.filter(member=mme.member2, event=AvailableEvent.objects.get(name=e, generated_competition_settings=generated_competition_settings)))!=0):
                    total_preference_score-=worst_preference_amount*0.5 # can change this constant

        for m in team[e]:
            # member-event preferences
            if e in members_to_ranked_preferences[m]: # event is one of the member's preferences
                total_preference_score+=members_to_ranked_preferences[m].index(e)
                # skill bonus
                # print(members_to_skill_level[m])
                total_skill_score-=1-(team_members.index(m)/len(team_members))
                # total_skill_score-=sum(members_to_skill_level[m].values())/len(members_to_skill_level[m]) # SHOULD DO RANKING INSTEAD PROB
            else: # event is not wanted by member
                # find similarities between event and member's preferred events
                total_num_of_similar_events = 0
                for wanted_e in members_to_ranked_preferences[m]:
                    for et in EventType.objects.filter(generated_competition_settings=generated_competition_settings):
                        #both events are in the same event type
                        if AvailableEvent.objects.get(generated_competition_settings=generated_competition_settings, name=wanted_e).event_type == et and AvailableEvent.objects.get(generated_competition_settings=generated_competition_settings, name=e).event_type == et:
                            total_num_of_similar_events += 1
                if len(members_to_ranked_preferences[m])!=0:
                    total_preference_score += worst_preference_amount*5 - total_num_of_similar_events/len(members_to_ranked_preferences[m]) # WHAT IF NO PREFERENCES
                else:
                    total_preference_score += worst_preference_amount
            # skills
            # if did the event before
            if e in members_to_experience[m]:
                # if did the event enough times to count
                if members_to_experience[m][e]>=generated_competition_settings.min_event_experience:
                    total_skill_score-=members_to_skill_level[m][e]
    return total_preference_score*(1-generated_competition_settings.skill_vs_preferences) + total_skill_score*generated_competition_settings.skill_vs_preferences+sum(empty_spots)*10000+len(required_member_event_preferences_not_yet_fulfilled)*1000


def fix_teams(teams, team_members_list, members_to_skill_level, members_to_ranked_preferences, generated_competition_settings, teams_list, events_with_3_members, member_member_event_pairs, worst_preference_amount, members_to_experience, build_events):
    result = []
    for t in range(len(teams_list)):
        members_to_events = {m:[e for e in teams_list[t] if m in teams_list[t][e]] for m in team_members_list[t]}
        members_that_need_more_events = [m for m in members_to_events.keys() if len(members_to_events[m])<generated_competition_settings.min_events_per_member]
        most_amount_of_events_occupied_by_member = max(members_to_events.values())
        members_that_can_give_away_events = [x[0] for x in list(sorted([(m, team_members_list[t].index(m)) for m in list(members_to_events.keys()) if (len(members_to_events[m])>generated_competition_settings.min_events_per_member and len(members_to_events[m])==most_amount_of_events_occupied_by_member)], key=lambda item: item[1], reverse=True))]
        temp_team = copy.deepcopy(teams_list[t])
        required_member_event_pairs = [[me.member.name, me.event.name] for me in WantedMemberEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings, required = True)]
        best_team = copy.deepcopy(temp_team)
        for m0 in members_that_need_more_events:
            orig_team = copy.deepcopy(best_team)
                # repeat until m0 has enough events
            while len([e for e in best_team if m0 in best_team[e]])<generated_competition_settings.min_events_per_member:
                changed = False
                best_score = float("inf")
                orig_team = copy.deepcopy(best_team)
                # print(best_team)
                members_to_events = {m:[e for e in best_team if m in best_team[e]] for m in team_members_list[t]}
                members_that_need_more_events = [m for m in members_to_events.keys() if len(members_to_events[m])<generated_competition_settings.min_events_per_member]
                most_amount_of_events_occupied_by_member = max([len(x) for x in members_to_events.values()])
                #FIX: NOT IMPORTANT TO ORDER BY SKILL LEVEL!!!
                members_that_can_give_away_events = [x[0] for x in list(sorted([(m, team_members_list[t].index(m)) for m in list(members_to_events.keys()) if (len(members_to_events[m])>generated_competition_settings.min_events_per_member and len(members_to_events[m])==most_amount_of_events_occupied_by_member)], key=lambda item: item[1], reverse=True))]
                # print(members_to_events)
                # print(members_that_need_more_events)
                # print(most_amount_of_events_occupied_by_member)
                # print(members_that_can_give_away_events)
                for m1 in members_that_can_give_away_events:
                    for event in members_to_events[m1]:
                        if [m1, event] not in required_member_event_pairs:
                            temp_team = copy.deepcopy(orig_team)
                            del temp_team[event][temp_team[event].index(m1)]
                            if is_valid_team_addition(event, m0, temp_team, teams[t], generated_competition_settings, events_with_3_members, build_events):
                                temp_team[event].append(m0)
                                members_to_events_temp_team = {m:[e for e in temp_team if m in temp_team[e]] for m in team_members_list[t]}
                                number_of_events_of_members_with_less_than_min = sum([generated_competition_settings.min_events_per_member-len(members_to_events_temp_team[m]) for m in members_to_events_temp_team if len(members_to_events_temp_team[m])<generated_competition_settings.min_events_per_member])
                                # (team, team_members, members_to_ranked_preferences, member_member_event_pairs, generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience)
                                team_score = calculate_preferences_score(temp_team,  team_members_list[t], members_to_ranked_preferences, member_member_event_pairs, generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience)+number_of_events_of_members_with_less_than_min*1000
                                if team_score<best_score:
                                    best_score = team_score
                                    best_team = temp_team
                                    changed = True
                if changed==False:
                    break
        result.append(best_team)
    return result

# test more at later date?
def improve_teams(teams, team_members_list, members_to_skill_level, members_to_ranked_preferences, generated_competition_settings, teams_list, events_with_3_members, member_member_event_pairs, worst_preference_amount, members_to_experience):
    result = []
    for t in range(len(teams_list)):
        members_to_events = {m:[e for e in teams_list[t] if m in teams_list[t][e]] for m in team_members_list[t]}
        best_team = copy.deepcopy(teams_list[t])
        best_score = float("inf")
        done_member_switches = []
        for m0 in team_members_list[t]:
            print("orig_team", best_team)
            orig_team = copy.deepcopy(best_team)
            members_to_events = {m:[e for e in orig_team if m in orig_team[e]] for m in team_members_list[t]}
            for m1 in team_members_list[t]:
                print(m0, m1)
                if m0 != m1 and (m0, m1) not in done_member_switches and (m1, m0) not in done_member_switches:
                    done_member_switches.append((m0, m1))
                    for e0 in members_to_events[m0]:
                        for e1 in members_to_events[m1]:
                            if e0 != e1:
                                print(e0, e1)
                                temp_team = copy.deepcopy(orig_team)
                                temp_team[e0].remove(m0)
                                if is_valid_team_addition(e0, m1, temp_team, teams[t], generated_competition_settings, events_with_3_members):
                                    temp_team[e0].append(m1)
                                    temp_team[e1].remove(m1)
                                    if is_valid_team_addition(e1, m0, temp_team, teams[t], generated_competition_settings, events_with_3_members):
                                        print("hi")
                                        print("temp team", temp_team)
                                        temp_team[e1].append(m0)
                                        team_score = calculate_preferences_score(temp_team,  team_members_list[t], members_to_ranked_preferences, member_member_event_pairs, generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience)
                                        if team_score<best_score:
                                            best_score = team_score
                                            best_team = temp_team
        result.append(best_team)
    return result


def check_if_valid_ranked_members_results(results, teams, required_members, seniors):
    for t in range(len(teams)):
        start_idx = sum([teams[i].team_size for i in range(0, t)]) if t!=0 else 0
        end_idx = min(sum([teams[t].team_size for t in range(0, t+1)]),len(results))
        # too many seniors
        if len([m for m in results[start_idx:end_idx] if m in seniors])>7:
            return False
        # reached end
        if end_idx == len(results):
            break
        # # RequiredMemberToTeam is not true
        # if RequiredMemberToTeam.objects.filter(member == teams)
    #not enough space for required members
    if sum([t.team_size for t in teams])-len([m for m in results if m not in required_members])<len([m for m in results if m in required_members]):
        return False
    return True

def check_score_of_ranked_members_results(results, ranked_members, teams, officers, required_members_on_specific_teams):
    total = sum([len(ranked_members)-ranked_members.index(m) for m in results])
    total -= sum([t.team_size for t in teams])-len(results)
    # print(results)
    
    for t in range(len(teams)):
        start_idx = sum([teams[i].team_size for i in range(0, t)]) if t!=0 else 0
        end_idx = min(sum([teams[t].team_size for t in range(0, t+1)]),len(results))
        # make sure required_members_on_specific_teams gets bonus
        # print("hii2")
        # print(required_members_on_specific_teams)
        # if "Ian Rozens" in results:
        #     print("hiii2")
        for member, team in required_members_on_specific_teams:
            # print(team==teams[t])
            # print(teams[t])
            # print(team)
            # print(member in results[start_idx: end_idx])
            if team==teams[t] and member in results[start_idx: end_idx]:
                # print("HIII")
                total += 1000
            elif team!=teams[t] and member in results[start_idx: end_idx]:
                total -= 1000
        # reached end
        if end_idx == len(results):
            break
    #officers get bonus
    for member in officers:
        if member in results[0:teams[0].team_size]:
            total += 10000
    # print(total)
    # if "Ian Rozens" in results:
    #     print(ERROR)
    return total


def generate_ranked_members(ranked_members, teams, officers, required_members, required_members_on_specific_teams, seniors):
    results = []
    ranked_members_copy = ranked_members.copy()
    while True:
        old_results = results
        best_score = float("-inf")
        best_member_addition = 0
        for m in ranked_members_copy:
            if check_if_valid_ranked_members_results(old_results+[m], teams, required_members, seniors):
                score = check_score_of_ranked_members_results(old_results+[m], ranked_members, teams, officers, required_members_on_specific_teams)
                if score>best_score:
                    best_score = score
                    best_member_addition = m
        # finished
        if best_member_addition == 0:
            # print(results)
            break
        else:
            ranked_members_copy.remove(best_member_addition)
            results.append(best_member_addition)
    for t in range(len(teams)):
        start_idx = sum([teams[i].team_size for i in range(0, t)]) if t!=0 else 0
        end_idx = min(sum([teams[t].team_size for t in range(0, t+1)]),len(results))
        #make sure officers are first
        results[start_idx:end_idx] = [m for m in results[start_idx:end_idx] if m in officers]+sorted([m for m in results[start_idx:end_idx] if m not in officers], key=lambda x: ranked_members.index(x))
    return results
    

          
# @login_required
# def generateTeams(request, pk):
#     generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
#     # teams that are in generated_competition_settings
#     teams = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings, is_displayed=True)
#     available_members = AvailableMember.objects.filter(generated_competition_settings = generated_competition_settings)
#     available_events = AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)
#     events_with_3_members = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, needs_3_members=True)]
#     build_events = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, is_build_event=True)]
#     results = []
#     error = ""
#     # check not too many seniors
#     # too many required seniors
#     print(RequiredMemberToTeam.objects.all())
#     for t in teams:
#         print([r.member.name+" "+t.name for r in RequiredMemberToTeam.objects.filter(team=t)])
#     # print([r.member.name+t.name for t in teams for r in RequiredMemberToTeam.objects.filter(team=t)])
#     if generated_competition_settings.user.id != request.user.id:
#         raise Http404
#     if len(teams)==0:
#         error="You need to add at least one team to generate!"
#     elif sum([t.team_size for t in teams])>len(available_members): # too many members on team, not possible!
#         error="The team sizes you specified are too large with the given members. Make the team size values lower to proceed."
#     # not enough event slots
#     elif any([t.generated_competition_settings.min_events_per_member*t.team_size>len(available_events)*2+len(events_with_3_members) for t in teams]):
#         error="There are not enough event slots given your high team size and high min events per member constraints. Please change before proceeding."
#     elif any([len(RequiredMemberToTeam.objects.filter(team=t))>t.team_size for t in teams]):
#         error="There are more required members to the team than is possible with your team_size constraint. Please change before proceeding."
#     #make sure none of the RequiredMemberToTeam objects overlap across different teams - done
#     # loading bar
#     # download teams csv file after generation
#     #make sure none of the RequiredMemberToTeam objects overlap across different teams
#     elif len(set([r.member.name for t in teams for r in RequiredMemberToTeam.objects.filter(team=t)]))!=len([r.member.name for t in teams for r in RequiredMemberToTeam.objects.filter(team=t)]):
#         error = "There are overlaps between required members on teams! Please change before proceeding."
#     else: # no errors!
#         #find preferences
#         member_event_pairs = WantedMemberEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings)
#         worst_preference_amount = max([m_e.rank for m_e in member_event_pairs]) if len(member_event_pairs)>0 else 0
#         member_member_event_pairs = WantedMemberMemberEventPair.objects.filter(member1__generated_competition_settings=generated_competition_settings)
#         members_to_ranked_preferences = dict()
#         officers = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, status="O")]
#         required_members = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, status="R", )]
#         required_members_on_specific_teams = [(r.member.name, r.team) for t in teams for r in RequiredMemberToTeam.objects.filter(team__generated_competition_settings = generated_competition_settings)]
#         seniors = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, is_senior=True)]
        
#         for me in member_event_pairs:
#             if me.member.name in members_to_ranked_preferences:
#                 members_to_ranked_preferences[me.member.name].append(me.event.name)
#             else:
#                 members_to_ranked_preferences[me.member.name]=[me.event.name]
#         # members with no ranked preferences
#         for m in available_members:
#             if m.name not in members_to_ranked_preferences:
#                 members_to_ranked_preferences[m.name]=[]
#         print(members_to_ranked_preferences)
        
#         #review previous competition data
#         available_members = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings)]
#         available_events = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)]
#         members_to_experience=dict()
#         members_to_skill_level=dict()
#         member_list=data.models.Member.objects.filter(event_member_instance__team__competition__user=request.user)
#         # min_score=float("inf")
#         # max_score=float("-inf")
#         for member in member_list: # for all the members
#             # print(members_to_skill_level)
#             # print(member)
#             # print(member.event_member_instance.event_name)
#             #they did not quit/get disqualified
#             if member.event_member_instance.score<=member.event_member_instance.team.competition.number_of_teams_competed:
#                 # calculate score for event_member_instance
#                 school_scores_of_competition=[]
#                 for team in data.models.Team.objects.filter(competition=member.event_member_instance.team.competition): # for all the teams in the member's competition
#                     school_scores_of_competition+=[x.score for x in data.models.EventMemberInstance.objects.filter(team=team) if x.score<=x.team.competition.number_of_teams_competed] # add the teams scores
#                 average_score_of_team=sum(school_scores_of_competition)/len(school_scores_of_competition)
#                 score=average_score_of_team/member.event_member_instance.team.competition.number_of_teams_competed-member.event_member_instance.score/member.event_member_instance.team.competition.number_of_teams_competed
#                 # if score>max_score:
#                 #     max_score=score
#                 # if score<min_score:
#                 #     min_score=score
#                 if member.name in members_to_skill_level:
#                     if member.event_member_instance.event_name in members_to_skill_level[member.name]:
#                         members_to_skill_level[member.name][member.event_member_instance.event_name]+=score
#                         members_to_experience[member.name][member.event_member_instance.event_name]+=1
#                     else:
#                         members_to_skill_level[member.name][member.event_member_instance.event_name]=score
#                         members_to_experience[member.name][member.event_member_instance.event_name]=1
#                 else:
#                     members_to_skill_level[member.name]={}
#                     members_to_skill_level[member.name][member.event_member_instance.event_name]=score
#                     members_to_experience[member.name]={}
#                     members_to_experience[member.name][member.event_member_instance.event_name]=1
#         max_sum_of_xp = max([sum(members_to_experience[m].values()) for m in members_to_experience])
#         print(members_to_skill_level)
#         # print(members_to_experience)
#         min_score = min([min(members_to_skill_level[m].values()) for m in members_to_skill_level])
#         max_score = max([max(members_to_skill_level[m].values()) for m in members_to_skill_level])
#         members_to_total_skill_level = {m:(sum(members_to_skill_level[m].values()) if m in members_to_skill_level else min_score*max_sum_of_xp) for m in available_members}
#         # scale members_to_skill_level to be between 0 and worst_preference_amount
#         # print(members_to_skill_level)
#         # k = worst_preference_amount/(max_score-min_score)
#         for m in members_to_skill_level:
#             for e in members_to_skill_level[m]:
#                 members_to_skill_level[m][e]=(members_to_skill_level[m][e]-min_score)/(max_score-min_score)
#         # print([m for m in available_members if m not in members_to_skill_level])
#         # members_to_total_skill_level = {m:(sum(members_to_skill_level[m].values()) if m in members_to_skill_level else min_score*max_sum_of_xp) for m in available_members}
#         # print("hi")
#         # print(worst_preference_amount)
#         # print(members_to_skill_level)
#         # members_to_total_skill_level = {m:(sum(members_to_skill_level[m].values()) if m in members_to_skill_level else min_score*max_sum_of_xp) for m in available_members}
#         # members_to_total_skill_level = {}
#         # for m in available_members:
#         #     if m in members_to_skill_level:
#         #         # print(members_to_skill_level[m] if m=="Raymond Tong" else "")
#         #         members_to_total_skill_level[m] = sum(members_to_skill_level[m].values())
#         #     else:
#         #         members_to_total_skill_level[m] = min_score*max_sum_of_xp
#         print("hi")
#         print(dict(sorted(members_to_total_skill_level.items(), key=lambda item:item[1])))
#         ranked_members = list(dict(sorted(members_to_total_skill_level.items(), key=lambda item:item[1], reverse=True)).keys())
#         print(ranked_members)
#         officers_to_total_skill_level = {o:members_to_total_skill_level[o] for o in members_to_total_skill_level if o in officers}
#         ranked_officers = list(dict(sorted(officers_to_total_skill_level.items(), key=lambda item: item[1], reverse=True)).keys())
#         number_of_members_included_in_competition = sum([t.team_size for t in teams])
#         ranked_members = ranked_officers + [m for m in ranked_members if m not in officers]
#         required_members_to_total_skill_level = {r:members_to_total_skill_level[r] for r in members_to_total_skill_level if r in required_members}
#         required_members_not_yet_on_team = [r for r in list(dict(sorted(required_members_to_total_skill_level.items(), key=lambda item: item[1], reverse=True)).keys()) if r in ranked_members[number_of_members_included_in_competition:]]
#         seniors_to_total_skill_level = {s:members_to_total_skill_level[s] for s in members_to_total_skill_level if s in seniors}
        
#         # #from the end to start, add required members not yet on team by replacing non-necessary members
#         # if required_members_not_yet_on_team!=[]:
#         #     for i, m in reversed(list(enumerate(ranked_members))):
#         #         if m not in required_members and m not in officers:
#         #             ranked_members[i] = required_members_not_yet_on_team.pop()
#         #             if required_members_not_yet_on_team==[]:
#         #                 break

#         # print(worst_preference_amount)
#         # print(members_to_skill_level)
#         # print(max_score)
#         # print(min_score)
#         # for t in range(len(teams)):
#         #     start_idx = sum([teams[t].team_size for t in range(0, t-1)]) if t!=0 else 0
#         #     end_idx = sum([teams[t].team_size for t in range(0, t)])
#         #     seniors_on_team = [m for m in ranked_members[start_idx:end_idx] if m in seniors and m in officers]+[m for m in ranked_members[start_idx:end_idx] if m in seniors and m in required_members]+[m for m in ranked_members[start_idx:end_idx] if m in seniors and m not in officers and m not in seniors]
            
#         #     if len(seniors_on_team)>7:
#         #         members_that_can_be_moved = [i for i in range(ranked_members) if ranked_members[i] not in seniors and ranked_members[i] not in officers]
#         #         for s in range(len(seniors_on_team)-7):
#         #             available_members_that_can_be_moved = [m for m in members_that_can_be_moved if m>=end_idx]
#         #             if available_members_that_can_be_moved!=[]:
#         #                 senior_idx = ranked_members.index(seniors_on_team[7+s])
#         #                 #choose closest switch_idx possible
#         #                 chosen_switch_idx = sorted(available_members_that_can_be_moved, key=lambda item: item-senior_idx)[0]
#         #                 #switch
#         #                 ranked_members[senior_idx], ranked_members[chosen_switch_idx] = ranked_members[chosen_switch_idx], ranked_members[senior_idx]
#         #                 #delete chosen_switch_idx from available_members_that_can_be_moved
#         #                 del available_members_that_can_be_moved[available_members_that_can_be_moved.index(chosen_switch_idx)]
        
#         # GENERATE TEAM MEMBERS

#         ranked_members = generate_ranked_members(ranked_members, teams, officers, required_members, required_members_on_specific_teams, seniors)
        
#         teams_list = []
#         print(ranked_members)
#         print(teams)
#         team_members_list = []
#         for t in range(len(teams)):
#             start_idx = sum([teams[i].team_size for i in range(0, t)]) if t!=0 else 0
#             end_idx = sum([teams[t].team_size for t in range(0, t+1)])
#             team_members = ranked_members[start_idx:end_idx]
#             print(team_members)
#             team = make_team(available_events, team_members, members_to_ranked_preferences, member_member_event_pairs, teams[t], generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience, build_events)
#             teams_list.append(team)
#             team_members_list.append(team_members)
#         # teams_list_new = improve_teams(teams, team_members_list, members_to_skill_level, members_to_ranked_preferences, generated_competition_settings, teams_list, events_with_3_members, member_member_event_pairs, worst_preference_amount, members_to_experience)
#         teams_list = fix_teams(teams, team_members_list, members_to_skill_level, members_to_ranked_preferences, generated_competition_settings, teams_list, events_with_3_members, member_member_event_pairs, worst_preference_amount, members_to_experience, build_events)
#         print(teams_list)
#         # print(teams_list)
#         #need to include new members in ranked_members too
#         # results = []
#         # print(teams_list)
#         # # format results for template rendering
#         # for t in range(len(teams_list)):
#         #     result = []
#         #     result.append([[e]+[m+" (*)" if e not in members_to_ranked_preferences[m] else m for m in teams_list[t][e]] for e in teams_list[t]])
#         #     result.append([[m]+[e if e in members_to_ranked_preferences[m] else e+" (*)" for e in [e for e in teams_list[t] if m in teams_list[t][e]]] for m in team_members_list[t]])
#         #     print(result)
#         #     results.append(result)
        
#         # save final team
#         # delete existing final team
#         FinalTeamEventPair.objects.filter(member__generated_competition_settings = generated_competition_settings).delete()
                
#         #delete unused teams
#         GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings, is_displayed=False, was_part_of_previous_generation=True).delete()
#         # iterate over teams
#         # generated_teams = GeneratedTeam.objects.filter(generated_competition_settings = generated_competition_settings)
#         for t in range(len(teams_list)):
#             team = teams[t]
#             team.was_part_of_previous_generation=True
#             team.save()
#             for e in teams_list[t]:
#                 event = AvailableEvent.objects.get(generated_competition_settings=generated_competition_settings, name=e)
#                 for m in teams_list[t][e]:
#                     member = AvailableMember.objects.get(generated_competition_settings=generated_competition_settings, name=m)
#                     member.final_team = team
#                     member.save()
#                     FinalTeamEventPair.objects.create(member = member, event=event, is_wanted= e in members_to_ranked_preferences[m])
#     return redirect('finalGeneratedCompetitionView', pk=generated_competition_settings.id)
#     # context = {
#     #     "error":error,
#     #     "results":results,
#     # }
#     # return render(request, "generation/generation.html", context)

# def finalGeneratedCompetitionView(request, pk):
#     generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
#     if request.user.id == generated_competition_settings.user.id:
#         teams = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings, was_part_of_previous_generation=True)
#         print(teams)
#         results = []
#         # if FinalTeamEventPair.objects.filter(FinalTeamEventPair.objects.filter(member__final_team = t))
#         for t in teams:
#             final_team_event_pairs = FinalTeamEventPair.objects.filter(member__final_team = t)
#             if len(final_team_event_pairs)>0:
#                 results1 = {}
#                 results2 = {}
#                 for f in final_team_event_pairs:
#                     member_name = f.member.name
#                     event_name = f.event.name
#                     extra = "" if f.is_wanted else "(*)"
#                     # results1
#                     if member_name in results1:
#                         results1[member_name].append(event_name+extra)
#                     else:
#                         results1[member_name]=[event_name+extra]
                    
#                     #results2
#                     if event_name in results2:
#                         results2[event_name].append(member_name+extra)
#                     else:
#                         results2[event_name] = [member_name+extra]
#                 results1 = dict(sorted(results1.items()))
#                 results2 = dict(sorted(results2.items()))
#                 print(results1)
#                 # results1.sort()
#                 # results2.sort()
#                 results.append([[[e]+results2[e]+[""]*(3-len(results2[e])) for e in results2],[[m]+results1[m] for m in results1]])
#         print(results)
#         context = {
#             "results" : results,
#         }
#         return render(request, "generation/generation.html", context)
#     raise Http404

def frontend_generate(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if generated_competition_settings.user.id == request.user.id:
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
        
        # print(required_members)
        # required_members_on_specific_teams = {str(t.id):[] for t in teams}
        # print(required_members_on_specific_teams)
        # for r_member in RequiredMemberToTeam.objects.filter(team__generated_competition_settings = generated_competition_settings):
        #     required_members_on_specific_teams[str(r_member.team.id)].append(r_member.member.name)
        # print(required_members_on_specific_teams)
        # required_members_on_specific_teams = [[r.member.name, r.team] for t in teams for r in RequiredMemberToTeam.objects.filter(team__generated_competition_settings = generated_competition_settings)]
        seniors = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, is_senior=True)]
        conflicting_events=[[e.name for e in AvailableEvent.objects.filter(conflict=c, generated_competition_settings=generated_competition_settings)] for c in ConflictingEvents.objects.filter(generated_competition_settings=generated_competition_settings)]
        event_types = [[e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, event_type = et)] for et in EventType.objects.filter(generated_competition_settings=generated_competition_settings)]
        
        # required_member_event_pairs = [[me.member.name, me.event.name] for me in WantedMemberEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings, required = True)]
        # print(required_member_event_pairs)
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
        members_to_experience=dict()
        members_to_skill_level=dict()   
                
        # member_list=[m for m in data.models.Member.objects.filter(event_member_instance__team__competition__user=request.user) if m.name in available_members]
        # print(available_members)
        # print(member_list)
        # average_scores_of_competition_cache = {}
        members_to_skill_level = dict()
        members_to_experience = dict()
        # members_to_data = dict()
        # first_time_scores = {e:[] for e in available_events}
        # all_events=set()
        for c in data.models.Competition.objects.filter(user=request.user).order_by('date'):
            emis_list = data.models.EventMemberInstance.objects.filter(team__competition=c)
            school_scores_of_competition = [x.score for x in data.models.EventMemberInstance.objects.filter(team__competition=c) if x.score<=x.team.competition.number_of_teams_competed]
            average_score_of_team=sum(school_scores_of_competition)/len(school_scores_of_competition)
            competition_difficulty = average_score_of_team/c.number_of_teams_competed
            for emi in emis_list:
                # all_events.add(emi.event_name)
                if emi.score <= c.number_of_teams_competed and emi.event_name in available_events: # don't count if disqualified or event_name not in available_events
                    score = competition_difficulty * (c.number_of_teams_competed - emi.score)/(c.number_of_teams_competed)
                    event = emi.event_name
                    members = [m.name for m in data.models.Member.objects.filter(event_member_instance = emi)]
                    
                    for m in members:
                        if m in members_to_experience:
                            if event in members_to_experience[m]:
                                members_to_experience[m][event] += 1
                                # members_to_data[m][event] += "<li>"+c.name+" "+emi.team.name+": ranked "+str(emi.score)+"/"+str(c.number_of_teams_competed)+" in "+emi.event_name+"</li>"
                            else:
                                members_to_experience[m][event] = 1
                                members_to_skill_level[m][event] = 0
                                # members_to_data[m][event] = "<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+c.name+" "+emi.team.name+": ranked "+str(emi.score)+"/"+str(c.number_of_teams_competed)+" in "+emi.event_name+"</li>"
                        else:
                            members_to_experience[m] = {}
                            # members_to_data[m] = {}
                            members_to_skill_level[m] = {}
                            members_to_skill_level[m][event] = 0
                            # members_to_data[m][event] = "<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+c.name+" "+emi.team.name+": ranked "+str(emi.score)+"/"+str(c.number_of_teams_competed)+" in "+emi.event_name+"</li>"
                            members_to_experience[m][event] = 1
                    # total_experience = sum([members_to_experience[member][event] for member in members])
                    # total_skill = sum([members_to_skill_level[member][event] for member in members])
                    for m in members:
                        # if total_skill != 0:
                            # members_to_skill_level[m][event] += membrs_to_skill_level[m][event]/total_skill*score
                        # else:
                        # if members_to_experience[m][event]==1: # first time
                        #     first_time_scores[event].append(members_to_experience[m][event]/total_experience * score)
                        members_to_skill_level[m][event] += score

        #shuffle dictionary to ensure randomness if two or more people have skills are the same
        keys = list(members_to_skill_level.keys())
        random.shuffle(keys)
        members_to_skill_level={key:members_to_skill_level[key] for key in keys}
        # print("hi4")
        # print(members_to_skill_level)
        members_to_experience={key:members_to_experience[key] for key in keys}

        min_total_score = min([sum(members_to_skill_level[m].values()) for m in members_to_skill_level])
        # members_to_total_skill_level = {m:(sum(members_to_skill_level[m].values()) if m in members_to_skill_level else min_total_score) for m in available_members}
        
        for m in members_to_experience:
            new_member_to_skill_level = dict()
            for e in members_to_experience[m]:
                if members_to_experience[m][e] != 1: # only did event once in the past, invalid
                    new_member_to_skill_level[e] = members_to_skill_level[m][e]
            # if not new_member_to_skill_level:
            #     del members_to_skill_level
            members_to_skill_level[m] = new_member_to_skill_level
        
        # print(members_to_skill_level)
        # print(members_to_skill_level["Ada Langford"].values())
        # print([min(members_to_skill_level[m].values()) for m in members_to_skill_level])
        min_score = min([min(members_to_skill_level[m].values(), default = float('inf')) for m in members_to_skill_level])
        max_score = max([max(members_to_skill_level[m].values(), default = float('-inf')) for m in members_to_skill_level])
        # max_score = max([max(members_to_skill_level[m].values()) for m in members_to_skill_level])
        
        # first_time_scores = {e: sum(first_time_scores[e])/len(first_time_scores[e]) if len(first_time_scores[e]) != 0 else 0.0 for e in first_time_scores}
        print("min_score", min_score)
        # for m in members_to_experience:
        #     for e in members_to_experience[m]:
        #         if members_to_experience[m][e] == 1:
        #             members_to_skill_level[m][e] = min_score
        # scale members_to_skill_level to be between 0 and 1
        for m in members_to_skill_level:
            # for e in available_events:
                # if e not in members_to_skill_level[m]:
                #     members_to_skill_level[m][e] = first_time_scores[e]
            # for e in members_to_skill_level[m]:
            #     members_to_skill_level[m][e]=(members_to_skill_level[m][e]-min_score)/(max_score-min_score)
            # member_to_events_skills = members_to_skill_level[m].copy()
            # while len(members_to_skill_level[m])>0:
            for e in available_events:
                if e not in members_to_skill_level[m]:
                    members_to_skill_level[m][e] = 0
                else:
                    members_to_skill_level[m][e] = (members_to_skill_level[m][e] - min_score) / (max_score - min_score)
            members_to_skill_level[m]=dict(sorted(members_to_skill_level[m].items(), key=lambda item: item[1], reverse=True))
        
        # for m in members_to_skill_level:
        #     members_to_skill_level[m]= {}
        
        print(members_to_skill_level)
        # members_to_skill_level = 
        # members_to_skill_level = {
        #     m: {
        #         **{e: members_to_skill_level[m][e] for e in members_to_skill_level[m] if e in available_events},
        #         **{e2: 0.0 for e2 in available_events if e2 not in members_to_skill_level[m]}
        #     }
        #     for m in members_to_skill_level if m in available_members
        # }        
        
        # rank the members
        # ranked_members = list(dict(sorted(members_to_total_skill_level.items(), key=lambda item:item[1], reverse=True)).keys())
                
        # GENERATE TEAM MEMBERS
        # print("hi33")
        # print(members_to_skill_level)
        # print(members_to_total_skill_level)
        # print(ranked_members)
        # print(teams)
        # print("officers")
        # print(officers)
        # print(required_members)
        # print(required_members_on_specific_teams)
        # print(seniors)
        # ranked_members = generate_ranked_members(ranked_members, teams, officers, required_members, required_members_on_specific_teams, seniors)
        # required_members = 
        # print(ranked_members)
        print(required_members)
        print([None if not t else t for t in required_members])
        context = {
            # "available_members" : available_members,
            # "required_members_on_specific_teams" : required_members_on_specific_teams,
            "id" : pk,
            "required_members_on_events" : required_members_on_events,
            "required_members" : required_members,
            "seniors" : seniors,
            "teams" : [t.team_size for t in teams],
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
        # print(context)
        return render(request, "generation/generation_frontend.html", context)
    raise Http404

# def calculate_preferences_score_2(team, team_members, members_to_ranked_preferences, member_member_event_pairs, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience, required_member_event_pairs, event_types, min_event_experience, skill_vs_preferences):
    
#     # goal: get lowest total_preference_score
    
#     # extra penalties
#     empty_spots = [2-len(team[e])+int(e in events_with_3_members) for e in team]
#     required_member_event_preferences_not_yet_fulfilled = [me for me in required_member_event_pairs if me[0] not in team[me[1]]]
    
#     # counters
#     total_preference_score = 0
#     total_skill_score = 0


#     for e in team:
#         # member-member-event preferences
#         for mme in member_member_event_pairs:
#             if mme[2] is None or mme[2]==e:
#                 # if both m1 and m2 in event
#                 if {mme[0], mme[1]} <= set(team[e]):
#                     total_preference_score-=worst_preference_amount
#                 #           there is empty space for the event               one of the members is in the event          both members are part of the team                                           both members want to do the event
#                 elif len(team[e])<2+int(e in events_with_3_members) and (mme[0] in team[e] or mme[1] in team[e]) and {mme[0], mme[1]}<=set(team_members) and (mme[2] in members_to_ranked_preferences[mme[0]] and mme[2] in members_to_ranked_preferences[mme[1]]):
#                     total_preference_score-=worst_preference_amount*0.5 # can change this constant

#         for m in team[e]:
#             # member-event preferences
#             # if event is one of the member's preferences
#             if e in members_to_ranked_preferences[m]:
#                 total_preference_score+=members_to_ranked_preferences[m].index(e)
#                 # skill bonus
#                 total_skill_score-=1-(team_members.index(m)/len(team_members))
#             else: # event is not wanted by member
#                 # find similarities between event and member's preferred events
#                 total_num_of_similar_events = 0
#                 for wanted_e in members_to_ranked_preferences[m]:
#                     for et in event_types:
#                         #both events are in the same event type
#                         if e in et and wanted_e in et:
#                             total_num_of_similar_events += 1
#                 if len(members_to_ranked_preferences[m])!=0:
#                     total_preference_score += worst_preference_amount*5 - total_num_of_similar_events/len(members_to_ranked_preferences[m]) # WHAT IF NO PREFERENCES
#                 else:
#                     total_preference_score += worst_preference_amount
#             # skills
#             # if did the event before
#             if e in members_to_experience[m]:
#                 # if did the event enough times to count
#                 if members_to_experience[m][e]>=min_event_experience:
#                     total_skill_score-=members_to_skill_level[m][e]
#     return total_preference_score*(1-skill_vs_preferences) + total_skill_score*skill_vs_preferences+sum(empty_spots)*10000+len(required_member_event_preferences_not_yet_fulfilled)*1000

# import copy

# def fix_teams2(teams, team_members_list, members_to_skill_level, members_to_ranked_preferences, min_events_per_member, teams_list, events_with_3_members, member_member_event_pairs, worst_preference_amount, members_to_experience, build_events, required_member_event_pairs):
#     result = []
#     for t in range(len(teams_list)):
#         members_to_events = {m:[e for e in teams_list[t] if m in teams_list[t][e]] for m in team_members_list[t]}
#         members_that_need_more_events = [m for m in members_to_events.keys() if len(members_to_events[m])<min_events_per_member]
#         most_amount_of_events_occupied_by_member = max(members_to_events.values())
#         members_that_can_give_away_events = [x[0] for x in list(sorted([(m, team_members_list[t].index(m)) for m in list(members_to_events.keys()) if (len(members_to_events[m])>min_events_per_member and len(members_to_events[m])==most_amount_of_events_occupied_by_member)], key=lambda item: item[1], reverse=True))]
#         best_team = copy.deepcopy(teams_list[t])
#         for m0 in members_that_need_more_events:
#             orig_team = copy.deepcopy(best_team)
#                 # repeat until m0 has enough events
#             while len([e for e in best_team if m0 in best_team[e]])<min_events_per_member:
#                 changed = False
#                 best_score = float("inf")
#                 orig_team = copy.deepcopy(best_team)
#                 # print(best_team)
#                 members_to_events = {m:[e for e in best_team if m in best_team[e]] for m in team_members_list[t]}
#                 members_that_need_more_events = [m for m in members_to_events.keys() if len(members_to_events[m])<min_events_per_member]
#                 most_amount_of_events_occupied_by_member = max([len(x) for x in members_to_events.values()])
#                 #FIX: NOT IMPORTANT TO ORDER BY SKILL LEVEL!!!
#                 members_that_can_give_away_events = [x[0] for x in list(sorted([(m, team_members_list[t].index(m)) for m in list(members_to_events.keys()) if (len(members_to_events[m])>min_events_per_member and len(members_to_events[m])==most_amount_of_events_occupied_by_member)], key=lambda item: item[1], reverse=True))]
#                 # print(members_to_events)
#                 # print(members_that_need_more_events)
#                 # print(most_amount_of_events_occupied_by_member)
#                 # print(members_that_can_give_away_events)
#                 for m1 in members_that_can_give_away_events:
#                     for event in members_to_events[m1]:
#                         if (m1, event) not in required_member_event_pairs:
#                             temp_team = copy.deepcopy(orig_team)
#                             del temp_team[event][temp_team[event].index(m1)]
#                             if is_valid_team_addition(event, m0, temp_team, teams[t], generated_competition_settings, events_with_3_members, build_events):
#                                 temp_team[event].append(m0)
#                                 members_to_events_temp_team = {m:[e for e in temp_team if m in temp_team[e]] for m in team_members_list[t]}
#                                 number_of_events_of_members_with_less_than_min = sum([min_events_per_member-len(members_to_events_temp_team[m]) for m in members_to_events_temp_team if len(members_to_events_temp_team[m])<min_events_per_member])
#                                 # (team, team_members, members_to_ranked_preferences, member_member_event_pairs, generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience)
#                                 team_score = calculate_preferences_score(temp_team,  team_members_list[t], members_to_ranked_preferences, member_member_event_pairs, generated_competition_settings, events_with_3_members, worst_preference_amount, members_to_skill_level, members_to_experience)+number_of_events_of_members_with_less_than_min*1000
#                                 if team_score<best_score:
#                                     best_score = team_score
#                                     best_team = temp_team
#                                     changed = True
#                 if changed==False:
#                     break
#         result.append(best_team)
#     return result

