from django.shortcuts import render
# import random
from .models import *
from .forms import *
# import string
import csv
# from django.http import HttpResponseRedirect
# from django.urls import reverse
# from formtools.wizard.views import SessionWizardView
import data.models
import copy
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
# from django.core import serializers
import json
import math
import time
from scipy.optimize import minimize
import numpy as np
from collections import defaultdict


# Create your views here.

def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces, then title-case
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.replace("(B)", "").replace("(3)", "").replace("&", "and") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)", "") if c.isalpha() or c==" "])
    return input_string.strip().title()

PASTEL_COLORS = ["FFE9D0", "FFFED3", "BBE9FF", "B1AFFF", "E7F0DC", "E7D4B5", "EF9C66", "C8CFA0", "E1ACAC", "E1AFD1", "E493B3"]

def available_events_reader(available_events, generated_competition_settings):
    reader = csv.reader(available_events.splitlines(), delimiter=',')

    color_idx = 0
    for row in reader:
        # skip empty rows
        if not row or remove_punctuation(row[0], True) == "":
            continue
        color = PASTEL_COLORS[color_idx % len(PASTEL_COLORS)]
        event_type=EventType.objects.create(generated_competition_settings=generated_competition_settings, color=color)
        color_idx += 1
        for e in row:
            event_name=remove_punctuation(e, True)
            if event_name!="":
                needs_3_members = "(3)" in e
                is_build_event = "(B)" in e
                AvailableEvent.objects.create(name=event_name, needs_3_members=needs_3_members, generated_competition_settings=generated_competition_settings, event_type=event_type, is_build_event=is_build_event)
            else: # reached end of row
                break

def conflicting_events_reader(conflicting_events, generated_competition_settings):
    reader = csv.reader(conflicting_events.splitlines(), delimiter=',')
    for row in reader:
        # skip empty rows
        if not row or remove_punctuation(row[0], True) == "":
            continue
        conflict = ConflictingEvents.objects.create(generated_competition_settings=generated_competition_settings)
        for e in row:
            event_name=remove_punctuation(e, True)
            # check if event exists
            if event_name!="":
                event_exists = AvailableEvent.objects.filter(name=event_name, generated_competition_settings=generated_competition_settings).exists()
                if event_exists:
                    event = AvailableEvent.objects.get(name=event_name, generated_competition_settings=generated_competition_settings)
                    event.conflict = conflict
                    event.save()
            else:
                break

def member_event_preferences_reader(member_event_preferences_data, generated_competition_settings):
    reader = csv.reader(member_event_preferences_data.splitlines(), delimiter=',')
    for row in reader:
        if not row:
            continue
        member_name=row[0]
        is_senior = "(S)" in member_name
        member_name=remove_punctuation(member_name, False)
        # skip rows with empty member name
        if member_name == "":
            continue
        member = AvailableMember.objects.create(generated_competition_settings=generated_competition_settings, name=member_name, is_senior=is_senior)
        e_idx = 0
        for event in row[1:]:
            event_name = remove_punctuation(event, True)
            if event_name!="":
                event_exists = AvailableEvent.objects.filter(name=event_name, generated_competition_settings=generated_competition_settings).exists()
                if event_exists:
                    e_idx += 1
                    event = AvailableEvent.objects.get(name=event_name, generated_competition_settings=generated_competition_settings)
                    WantedMemberEventPair.objects.create(rank=e_idx, event=event, member=member)

def member_member_event_preferences_reader(member_member_event_preferences_data, generated_competition_settings):
    # read member_member_event_preferences_data
    reader = csv.reader(member_member_event_preferences_data.splitlines(), delimiter=',')

    for row in reader:
        try:
            member_1_name = remove_punctuation(row[0], False)
            member_1 = AvailableMember.objects.get(generated_competition_settings=generated_competition_settings, name=member_1_name)
            member_2_name = remove_punctuation(row[1], False)
            member_2 = AvailableMember.objects.get(generated_competition_settings=generated_competition_settings, name=member_2_name)
            event_name = remove_punctuation(row[2], True)
            if event_name == "":
                continue  # skip general (non-event-specific) partner preferences
            event = AvailableEvent.objects.get(name=event_name, generated_competition_settings=generated_competition_settings)
            WantedMemberMemberEventPair.objects.create(member1=member_1, member2=member_2, event=event)
        except:
            continue

@login_required
def competitionSettingsFormView(request):
    form = CompetitionSettingsForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            # make initial settings constants
            generated_competition_settings = GeneratedCompetitionSettings.objects.create(user=request.user,
                                                                                         name = form.cleaned_data.get("name"),
                                                                                         notes = form.cleaned_data.get("notes"),
                                                                                         max_events_per_member = form.cleaned_data.get("max_events_per_member"),
                                                                                         min_events_per_member = form.cleaned_data.get("min_events_per_member"),
                                                                                         skill_vs_preferences = form.cleaned_data.get("skill_vs_preferences"),
                                                                                         max_num_of_build_events_per_member = form.cleaned_data.get("max_num_of_build_events_per_member"),
                                                                                         use_ranking = form.cleaned_data.get("use_ranking"),
                                                                                         partner_preference_weight = form.cleaned_data.get("partner_preference_weight"),
                                                                                         randomization = form.cleaned_data.get("randomization"))
            
            #analyze files
            available_events = form.cleaned_data["available_events"] or None
            conflicting_events = form.cleaned_data["conflicting_events"] or None
            member_event_preferences_data = form.cleaned_data["member_event_preferences_data"] or None
            member_member_event_preferences_data = form.cleaned_data["member_member_event_preferences_data"] or None

            # read available_events if it exists
            if available_events is not None:
                available_events_reader(available_events, generated_competition_settings)

            # read conflicting_events if it exists
            if conflicting_events is not None:
                conflicting_events_reader(conflicting_events, generated_competition_settings)

            # read member_event_preferences_data if it exists
            if member_event_preferences_data is not None:
                member_event_preferences_reader(member_event_preferences_data, generated_competition_settings)

            # read member_member_event_preferences_data if it exists
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
        form = CompetitionSettingsEditForm(request.POST or None, instance=generated_competition_settings)
        if request.method == "POST":
            if form.is_valid():                
                # make initial settings constants
                generated_competition_settings.name = form.cleaned_data.get("name")
                generated_competition_settings.notes = form.cleaned_data.get("notes")
                generated_competition_settings.max_events_per_member = form.cleaned_data.get("max_events_per_member")
                generated_competition_settings.min_events_per_member = form.cleaned_data.get("min_events_per_member")
                generated_competition_settings.skill_vs_preferences = form.cleaned_data.get("skill_vs_preferences")
                generated_competition_settings.max_num_of_build_events_per_member = form.cleaned_data.get("max_num_of_build_events_per_member")
                generated_competition_settings.use_ranking = form.cleaned_data.get("use_ranking")
                generated_competition_settings.partner_preference_weight = form.cleaned_data.get("partner_preference_weight")
                generated_competition_settings.randomization = form.cleaned_data.get("randomization")
                generated_competition_settings.save()
                
                return redirect("generatedCompetitionSettingsView", pk=generated_competition_settings.id)
                        
        context={
            "form":form,
            "generated_competition_settings":generated_competition_settings,
        }
        return render(request, 'generation/edit_settings.html', context)
    raise Http404


@login_required
def generatedCompetitionSettingsView(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if generated_competition_settings.user.id == request.user.id:
        if request.method == "POST":
            action = request.POST.get("action")
            team_id = request.POST.get("team_id")
            if action in ("move_up", "move_down") and team_id:
                team = get_object_or_404(GeneratedTeam, id=team_id, generated_competition_settings=generated_competition_settings)
                if action == "move_up":
                    above = GeneratedTeam.objects.filter(
                        generated_competition_settings=generated_competition_settings,
                        order__lt=team.order
                    ).order_by('-order').first()
                    if above:
                        above.order, team.order = team.order, above.order
                        above.save()
                        team.save()
                elif action == "move_down":
                    below = GeneratedTeam.objects.filter(
                        generated_competition_settings=generated_competition_settings,
                        order__gt=team.order
                    ).order_by('order').first()
                    if below:
                        below.order, team.order = team.order, below.order
                        below.save()
                        team.save()
            return redirect('generatedCompetitionSettingsView', pk=pk)
        team_list = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings)
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
        form=TeamForm(request.POST or None)
        if request.method=="POST":
            if form.is_valid():
                max_order = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings).order_by('-order').values_list('order', flat=True).first() or 0
                GeneratedTeam.objects.create(name=form.cleaned_data.get("name"),
                                             notes=form.cleaned_data.get("notes"),
                                             generated_competition_settings=generated_competition_settings,
                                             team_size=form.cleaned_data.get("team_size"),
                                             order=max_order + 1)
                return redirect('generatedCompetitionSettingsView', pk=generated_competition_settings.id)
        context={
            "form": form,
            "generated_competition_settings": generated_competition_settings,
        }
        return render(request, "generation/team_edit.html", context)
    raise Http404

@login_required
def generatedTeamEditView(request, pk):
    generated_team = get_object_or_404(GeneratedTeam, id=pk)
    
    if generated_team.generated_competition_settings.user.id == request.user.id:
        form = TeamForm(request.POST or None, instance=generated_team)
        if request.method=="POST":
            if form.is_valid():
                generated_team.name=form.cleaned_data.get("name")
                generated_team.notes=form.cleaned_data.get("notes")
                generated_team.team_size=form.cleaned_data.get("team_size")
                generated_team.save()
                return redirect('generatedCompetitionSettingsView', pk=generated_team.generated_competition_settings.id)
        context={
            "form":form,
            "generated_competition_settings": generated_team.generated_competition_settings,
            "generated_team": generated_team,
        }
        return render(request, "generation/team_edit.html", context)
    raise Http404

@login_required
def editRequirementsView(request, pk):
    generated_team = get_object_or_404(GeneratedTeam, id=pk)
    
    if generated_team.generated_competition_settings.user.id == request.user.id:
        member_queryset = AvailableMember.objects.filter(generated_competition_settings = generated_team.generated_competition_settings)
        event_queryset = AvailableEvent.objects.filter(generated_competition_settings = generated_team.generated_competition_settings)

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

                    
@login_required
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
            "generated_competition_settings":generated_competition_settings,
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
            "generated_competition_settings":team.generated_competition_settings,
            "generated_team":team,
        }
        return render(request, "generation/confirm_delete.html", context)
    raise Http404

@login_required
def frontend_generate(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)

    if generated_competition_settings.user.id != request.user.id:
        raise Http404
    
    # teams that are in generated_competition_settings
    teams = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings)
        
    if not data.models.SkillData.objects.filter(user=request.user).exists():
        data.models.SkillData.objects.create(user=request.user)
    skill_data = data.models.SkillData.objects.get(user=request.user)
    competition_list = data.models.Competition.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of competitions
    practice_list = data.models.Practice.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of practice instances
    instance_to_emis = dict() # dictionary that maps competitions or practice tests to dictionary that pairs (event, member) to observed skill
    instance_to_emi_data = dict()
    include_dq = skill_data.include_disqualifications
    me_to_skill = defaultdict(list)
    # Bulk-fetch all competition EMIs with members in 2 queries instead of N+1
    all_comp_emis = data.models.EventMemberInstance.objects.filter(
        team__competition__in=competition_list
    ).select_related('team__competition').prefetch_related('member_set')
    comp_results = {}
    comp_data = {}
    for emi in all_comp_emis:
        c = emi.team.competition
        members = [m.name for m in emi.member_set.all()]
        for m in members:
            if include_dq or emi.score <= c.number_of_teams_competed:
                me_to_skill[(m.lower(), emi.event_name.lower())].append(c)
                capped_score = min(emi.score, c.number_of_teams_competed)
                key = (m.lower(), emi.event_name.lower())
                if c not in comp_results:
                    comp_results[c] = {}
                    comp_data[c] = {}
                comp_results[c][key] = 1-(capped_score-1)/(c.number_of_teams_competed-1)
                comp_data[c][key] = emi
    for c in comp_results:
        if comp_results[c]:
            instance_to_emis[c] = comp_results[c]
            instance_to_emi_data[c] = comp_data[c]
    # Bulk-fetch all practice EMIs in 1 query instead of N
    all_practice_emis = data.models.EventMemberPracticeInstance.objects.filter(
        practice__in=practice_list
    ).select_related('practice')
    prac_results = {}
    prac_data = {}
    for emi in all_practice_emis:
        p = emi.practice
        member = emi.member_name.lower()
        key = (member, p.event_name.lower())
        me_to_skill[key].append(p)
        if p not in prac_results:
            prac_results[p] = {}
            prac_data[p] = {}
        prac_results[p][key] = emi.points_scored/p.total_points
        prac_data[p][key] = emi
    for p in prac_results:
        if prac_results[p]:
            instance_to_emis[p] = prac_results[p]
            instance_to_emi_data[p] = prac_data[p]
    
    instance_list = [i for i in instance_to_emis] # all the competitions that have data
    num_instances = len(instance_list) # number of valid competitions
    instance_to_idx = {instance_list[i]:i for i in range(num_instances)}
    instances_with_matches = [False for x in range(num_instances)]
    use_initial_skill = skill_data.use_initial_skill
    def custom_loss(params):
        skill_no_exp = params[-1]
        instance_loss = [0 for i in range(num_instances)]
        instance_frequency = [0 for i in range(num_instances)]
        for member, event in me_to_skill: # for each member, event pair
            instances = me_to_skill[(member, event)] # instance where member, event pair competed
            num_scores = len(instances) # num instances where member, event pair competed
            if not use_initial_skill and num_scores == 1:
                # skip single-data-point pairs when initial skill is disabled
                instance_idx = instance_to_idx[instances[0]]
                if num_scores>0:
                    instances_with_matches[instance_idx] = True
                instance_frequency[instance_idx]+=1
                continue
            scores = dict()
            sum_scores = 0
            for i in instances: # compute final scores
                instance_idx = instance_to_idx[i]
                if num_scores>0:
                    instances_with_matches[instance_idx] = True
                instance_frequency[instance_idx]+=1

                score = instance_to_emis[i][(member, event)]
                weight = params[instance_idx*2]
                bias = params[instance_idx*2+1]
                final_score = weight * score + bias
                scores[i]=final_score
                sum_scores += final_score

            for i in instances: # compute loss
                instance_idx = instance_to_idx[i]
                score = instance_to_emis[i][(member, event)]
                weight = params[instance_idx*2]
                bias = params[instance_idx*2+1]
                if num_scores != 1:
                    pred_final_score = (sum_scores-scores[i])/(num_scores-1)
                else:
                    pred_final_score = skill_no_exp
                pred_score = (pred_final_score - bias) / weight
                instance_loss[instance_idx]+=pow(pred_score-score, 2)
        total_loss = sum([instance_loss[i]/instance_frequency[i] for i in range(num_instances) if instance_frequency[i]>0])
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
        new_params = minimize(custom_loss, [0.5 if x%2 == 0 else 0 for x in range(num_instances*2+1)], options={"disp":False}, callback=callback, bounds=[(0, 1) if x%2 == 0 else (-0.5, 0.5) for x in range(num_instances*2+1)]).x
    except StopIteration:
        new_params = callback.best_result

    new_params = [float(p) for p in new_params]
    
    # Fetch all members and events in single queries, filter in Python
    all_member_objs = list(AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings))
    available_members = [m.name for m in all_member_objs]
    seniors = [m.name for m in all_member_objs if m.is_senior]

    all_event_objs = list(AvailableEvent.objects.filter(
        generated_competition_settings=generated_competition_settings
    ).select_related('event_type', 'conflict'))
    available_events = sorted([e.name for e in all_event_objs])
    available_events_ci = {e.lower(): e for e in available_events}
    available_members_ci = {m.lower(): m for m in available_members}
    events_with_3_members = [e.name for e in all_event_objs if e.needs_3_members]
    build_events = [e.name for e in all_event_objs if e.is_build_event]

    member_event_pairs = [(me.member.name, me.event.name, me.rank) for me in WantedMemberEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings)]

    worst_preference_amount = max([m_e[2] for m_e in member_event_pairs]) if len(member_event_pairs)>0 else 0
    member_member_event_pairs = [[mme.member1.name, mme.member2.name, mme.event.name] for mme in WantedMemberMemberEventPair.objects.filter(member1__generated_competition_settings=generated_competition_settings, event__isnull=False)]

    # Batch-fetch all requirements in 1 query instead of per-team
    all_requirements = RequiredMemberToTeam.objects.filter(
        team__in=teams
    ).select_related('member', 'event', 'team')
    required_members = [[] for _ in range(len(teams))]
    required_members_on_events = [[] for _ in range(len(teams))]
    team_to_idx = {teams[t].id: t for t in range(len(teams))}
    for r in all_requirements:
        t = team_to_idx[r.team_id]
        if r.member.name not in required_members[t]:
            required_members[t].append(r.member.name)
        if r.event is not None:
            required_members_on_events[t].append([r.member.name, r.event.name])

    # Build conflicts and event type groups from already-fetched event objects
    conflict_objects = ConflictingEvents.objects.filter(generated_competition_settings=generated_competition_settings)
    conflicting_events = [[e.name for e in all_event_objs if e.conflict_id == c.id] for c in conflict_objects]

    event_type_objects = EventType.objects.filter(generated_competition_settings=generated_competition_settings)
    event_types = [[e.name for e in all_event_objs if e.event_type_id == et.id] for et in event_type_objects]

    # build event_type_groups with color info for XLSX export
    event_type_groups = []
    for et in event_type_objects:
        et_events = [e.name for e in all_event_objs if e.event_type_id == et.id]
        if et_events:
            event_type_groups.append({"events": et_events, "color": et.color})
    # uncategorized events (event_type=None) get grey color
    uncat_events = [e.name for e in all_event_objs if e.event_type is None]
    if uncat_events:
        event_type_groups.append({"events": uncat_events, "color": "CCCCCC"})
        event_types.append(uncat_events)

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

    valid_weights = [new_params[w*2] for w in range(num_instances) if instances_with_matches[w]==True]
    valid_biases = [new_params[2*b+1] for b in range(num_instances) if instances_with_matches[b]==True]
    
    if len(valid_weights) == 0:
        average_weight = 0.5
        average_bias = 0
    else:
        average_weight = sum(valid_weights)/len(valid_weights)
        average_bias = sum(valid_biases)/len(valid_biases)
    for x in range(num_instances):
        if instances_with_matches[x]==False:
            new_params[x*2] = average_weight
            new_params[x*2+1] = average_bias
    
    # recompute everything from new_params
    members_to_skill_level = dict()
    members_to_experience = dict()
    
    skill_no_exp = new_params[-1]
    for member_lower, event_lower in me_to_skill: # for each member, event pair
        instances = me_to_skill[(member_lower, event_lower)] # instance where member, event pair competed
        canonical_event = available_events_ci.get(event_lower)
        if canonical_event is not None:
            canonical_member = available_members_ci.get(member_lower, member_lower.title())
            num_scores = len(instances) # num instances where member, event pair competed
            scores = dict()
            sum_scores = 0
            if canonical_member not in members_to_skill_level:
                members_to_experience[canonical_member] = {canonical_event:0}
                members_to_skill_level[canonical_member] = {canonical_event:0}
            for i in instances: # compute final scores
                instance_idx = instance_to_idx[i]
                emi = instance_to_emi_data[i][(member_lower, event_lower)]
                score = instance_to_emis[i][(member_lower, event_lower)]
                weight = new_params[instance_idx*2]
                bias = new_params[instance_idx*2+1]
                final_score = weight * score + bias
                scores[i]=final_score
                sum_scores += final_score
            # compute predicted scores
            pred_final_score = sum_scores / num_scores
            pred_score = (pred_final_score - average_bias) / average_weight + skill_data.experience_rate*num_scores
            members_to_skill_level[canonical_member][canonical_event] = pred_score
            members_to_experience[canonical_member][canonical_event] = num_scores


        for m in members_to_experience:
            for e in available_events:
                if e not in members_to_experience[m]:
                    members_to_experience[m][e] = 0
                    members_to_skill_level[m][e] = skill_no_exp if use_initial_skill else 0

    min_score = min([min(members_to_skill_level[m].values(), default = 0) for m in members_to_skill_level], default=0)
    max_score = max([max(members_to_skill_level[m].values(), default = 1) for m in members_to_skill_level], default=1)
    
    # scale members_to_skill_level to be between 0 and 1
    for m in members_to_skill_level:
        for e in available_events:
            if max_score - min_score != 0:
                members_to_skill_level[m][e] = (members_to_skill_level[m][e] - min_score) / (max_score - min_score)
            else:
                members_to_skill_level[m][e] = 0
        members_to_skill_level[m]=dict(sorted(members_to_skill_level[m].items(), key=lambda item: item[1], reverse=True))

    context = {
        "id" : pk,
        "required_members_on_events" : json.dumps(required_members_on_events),
        "required_members" : json.dumps(required_members),
        "seniors" : json.dumps(seniors),
        "teams" : json.dumps([t.team_size for t in teams]),
        "team_names" : json.dumps([t.name for t in teams]),
        "members_to_ranked_preferences" : json.dumps(members_to_ranked_preferences),
        "member_member_event_pairs" : json.dumps(member_member_event_pairs),
        "generated_competition_settings" : generated_competition_settings,
        "available_members" : json.dumps(available_members),
        "available_events" : json.dumps(available_events),
        "events_with_3_members" : json.dumps(events_with_3_members),
        "build_events" : json.dumps(build_events),
        "worst_preference_amount" : worst_preference_amount,
        "members_to_skill_level" : json.dumps(members_to_skill_level),
        "members_to_experience" : json.dumps(members_to_experience),
        "conflicting_events" : json.dumps(conflicting_events),
        "event_types" : json.dumps(event_types),
        "event_type_groups" : json.dumps(event_type_groups),
        "min_score" : min_score,
        "valid": teams.count()>0 and len(available_members)>0 and len(available_events)>0,
        "has_teams": teams.count()>0,
        "has_members": len(available_members)>0,
        "has_events": len(available_events)>0,
    }
    return render(request, "generation/generation_frontend.html", context)


# def frontend_generate(request, pk):
#     generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)

#     if generated_competition_settings.user.id != request.user.id:
#         raise Http404
    
#     if not data.models.SkillData.objects.filter(user=request.user).exists():
#         data.models.SkillData.objects.create(user=request.user)
#     skill_data = data.models.SkillData.objects.get(user=request.user)
#     competition_list = data.models.Competition.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of competitions
#     practice_list = data.models.Practice.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of practice instances
#     competition_to_emis = {} # dictionary that maps competitions to dictionary that pairs (event, member) to quartile
#     for c in competition_list: # for all the competitions
#         emis_list = data.models.EventMemberInstance.objects.filter(team__competition=c) # get all the events
#         results_dict = dict()
#         for emi in emis_list: # for each of the events
#             members = [m.name for m in data.models.Member.objects.filter(event_member_instance = emi)] # get all the members in event
#             for m in members: # for each member on the event
#                 if emi.score <= c.number_of_teams_competed: # if the score is a valid placement (not a DQ/no-show)
#                     results_dict[(emi.event_name, m)] = 1-emi.score/c.number_of_teams_competed
#         if results_dict:
#             competition_to_emis[c] = results_dict
#     for p in practice_list:
#         emis_list = data.models.EventMemberPracticeInstance.objects.filter(practice=p)
#         results_dict = dict()
#         for emi in emis_list:
#             member = emi.member_name
#             results_dict[(p.event_name, member)] = emi.points_scored/p.total_points
#         if results_dict:
#             competition_to_emis[p] = results_dict
    
#     all_list = [c for c in competition_to_emis] # all the competitions that have data
#     num_competitions = len(all_list) # number of valid competitions
#     no_matches_comps = set()
#     def custom_loss(params): # calculates math to minimize
#         discovered_experience_rate = abs(params[-2])
#         # skill_no_exp = abs(params[-1])
#         skill_no_exp = 0
#         total_loss = 0
#         for c1 in range(num_competitions): # comp to leave out
#             total_comp_loss = 0
#             total_num_repeats = 0
#             em_to_exp = dict()
#             for c2 in range(num_competitions): # for all other comps
#                 competition = all_list[c2] # other competition you are looking at
#                 if c1 != c2: # make sure the comp to leave out isn't equivalent to the other comp
#                     for event, member in competition_to_emis[competition]: # for all the scores in the other comp
#                         score = competition_to_emis[competition][(event, member)]
#                         weight = abs(params[c2]*2) # difficulty weight of competition
#                         bias = params[c2]*2+1
#                         # update event, member pair prev data
#                         if (event, member) in em_to_exp:
#                             num_times_member_did_event_previously = len(em_to_exp[(event, member)])+1
#                             # score -= discovered_experience_rate*(math.log(num_times_member_did_event_previously))
#                             score -= discovered_experience_rate*num_times_member_did_event_previously
#                             score = weight * score + bias
#                             em_to_exp[(event, member)].append(score)
#                         else:
#                             score = weight * score + bias
#                             em_to_exp[(event, member)] = [score]
#                 else: # if it's the competition to leave out, add the score None to people's data
#                     for event, member in competition_to_emis[competition]:
#                         score = None
#                         if (event, member) in em_to_exp:
#                             em_to_exp[(event, member)].append(score)
#                         else:
#                             em_to_exp[(event, member)] = [score]
#             no_matches = True # if the comp has no matches with other comps, then not possible so ignore
#             for event, member in em_to_exp: # for every event, member pair in em_to_exp data
#                 if None in em_to_exp[(event, member)]: # the event, member pair participated in left out competition
#                     total_num_repeats += 1 
#                     left_out_idx = em_to_exp[(event, member)].index(None) # index of left out comp
#                     num_other_instances = len(em_to_exp[(event, member)])-1
#                     if num_other_instances==0: # no other instances, left out comp is first time doing it
#                         pred = skill_no_exp
#                     else: # there exists other instances, calculate average of all other past instances
#                         no_matches = False
#                         pred = 0
#                         for i in range(num_other_instances+1):
#                             if i != left_out_idx:
#                                 pred += em_to_exp[(event, member)][i]/num_other_instances
#                     weight = abs(params[c1*2]) # difficulty weight of left out comp
#                     bias = params[c1*2+1] # bias of left out comp
#                     competition = all_list[c1]
#                     actual = competition_to_emis[competition][(event, member)] # actual score
#                     # pred = (pred - bias)/ weight + discovered_experience_rate*(math.log(left_out_idx+1))
#                     pred = (pred - bias)/ weight + discovered_experience_rate*(left_out_idx+1)
#                     total_comp_loss += (actual - pred)**2
#             if no_matches:
#                 no_matches_comps.add(c1)
#             else:
#                 total_loss += (total_comp_loss/total_num_repeats)/num_competitions

#         return total_loss
    
#     class TimeLimitCallback:
#         def __init__(self, time_limit):
#             self.start_time = time.time()
#             self.time_limit = time_limit
#             self.best_result = None

#         def __call__(self, xk):
#             elapsed_time = time.time() - self.start_time
#             if elapsed_time >= self.time_limit:
#                 raise StopIteration("Time limit reached")
#             self.best_result = xk
#     time_limit = 5 #seconds
#     callback = TimeLimitCallback(time_limit)
#     try:
#         new_params = minimize(custom_loss, np.asarray([0.5 for x in range(num_competitions*2+2)]), options={"disp":False}, callback=callback).x
#     except StopIteration:
#         new_params = callback.best_result
#     new_params = new_params.tolist()

#     # teams that are in generated_competition_settings
#     teams = GeneratedTeam.objects.filter(generated_competition_settings=generated_competition_settings)
#     available_members = [m.name for m in AvailableMember.objects.filter(generated_competition_settings = generated_competition_settings)]
#     available_events = sorted([e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)])
#     events_with_3_members = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, needs_3_members=True)]
#     build_events = [e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, is_build_event=True)]
    
#     member_event_pairs = [(me.member.name, me.event.name, me.rank) for me in WantedMemberEventPair.objects.filter(member__generated_competition_settings=generated_competition_settings)]

#     worst_preference_amount = max([m_e[2] for m_e in member_event_pairs]) if len(member_event_pairs)>0 else 0
#     member_member_event_pairs = [[mme.member1.name, mme.member2.name, mme.event.name] for mme in WantedMemberMemberEventPair.objects.filter(member1__generated_competition_settings=generated_competition_settings, event__isnull=False)]
#     required_members = []
#     required_members_on_events = []
#     for t in range(len(teams)):
#         requirements = RequiredMemberToTeam.objects.filter(team=teams[t])
#         t_required_members = []
#         t_required_members_on_events = []
#         for r in requirements:
#             if r.member.name not in t_required_members:
#                 t_required_members.append(r.member.name)
#             if r.event is not None:
#                 t_required_members_on_events.append([r.member.name, r.event.name])
#         required_members.append(t_required_members)
#         required_members_on_events.append(t_required_members_on_events)


#     seniors = [m.name for m in AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings, is_senior=True)]
#     conflicting_events=[[e.name for e in AvailableEvent.objects.filter(conflict=c, generated_competition_settings=generated_competition_settings)] for c in ConflictingEvents.objects.filter(generated_competition_settings=generated_competition_settings)]
#     event_types = [[e.name for e in AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings, event_type = et)] for et in EventType.objects.filter(generated_competition_settings=generated_competition_settings)]

#     members_to_ranked_preferences = dict()
#     # add members with ranked_preferences
#     for member, event, rank in member_event_pairs:
#         if member in members_to_ranked_preferences:
#             members_to_ranked_preferences[member].append((event, rank))
#         else:
#             members_to_ranked_preferences[member]=[(event, rank)]

#     # add members with no ranked preferences
#     for m in available_members:
#         if m not in members_to_ranked_preferences:
#             members_to_ranked_preferences[m]=[]

#     # sort members_to_ranked_preferences
#     members_to_ranked_preferences = {m:[p[0] for p in sorted(members_to_ranked_preferences[m], key= lambda x:x[1])] for m in members_to_ranked_preferences}
            
#     #review previous competition data
#     members_to_experience={m:{e:0 for e in available_events} for m in available_members}
#     members_to_skill_level={m:{e:0 for e in available_events} for m in available_members}


#     valid_weights = [new_params[w*2] for w in range(num_competitions) if w not in no_matches_comps]
#     valid_biases = [new_params[2*b+1] for b in range(num_competitions) if b not in no_matches_comps]
#     if len(valid_weights) == 0:
#         average_weight = 0.5
#         average_bias = 0
#     else:
#         average_weight = sum(valid_weights)/len(valid_weights)
#         average_bias = sum(valid_biases)/len(valid_biases)
#     for non_valid_comp in no_matches_comps:
#         new_params[non_valid_comp*2] = average_weight
#         new_params[non_valid_comp*2+1] = average_bias
    
    
#     discovered_experience_rate = abs(new_params[-2])
    
#     for c_idx in range(num_competitions):
#         c = all_list[c_idx]
#         if c in competition_list:
#             emis_list = data.models.EventMemberInstance.objects.filter(team__competition=c)
#             school_scores_of_competition = [x.score for x in data.models.EventMemberInstance.objects.filter(team__competition=c) if x.score<=x.team.competition.number_of_teams_competed]
#             if len(school_scores_of_competition) != 0:
#                 for emi in emis_list:
#                     if emi.score < c.number_of_teams_competed:
#                         weight = abs(new_params[c_idx*2])
#                         bias = new_params[c_idx*2+1]
#                         event = emi.event_name
#                         members = [m.name for m in data.models.Member.objects.filter(event_member_instance = emi)]
                        
#                         for m in members:
#                             if m in members_to_experience:
#                                 if event in members_to_experience[m]:
#                                     members_to_experience[m][event] += 1
#                                     score = 1-(emi.score/c.number_of_teams_competed)
#                                     # members_to_skill_level[m][event] += weight * (score - discovered_experience_rate*(math.log(members_to_experience[m][event]))) + bias
#                                     members_to_skill_level[m][event] += weight * (score - discovered_experience_rate*members_to_experience[m][event]) + bias
#         else:
#             emis_list = data.models.EventMemberPracticeInstance.objects.filter(practice=c)
#             for emi in emis_list:
#                 weight = abs(new_params[c_idx*2])
#                 bias = new_params[c_idx*2+1]
#                 event = emi.practice.event_name
#                 member = emi.member_name
                
#                 if member in members_to_experience:
#                     if event in members_to_experience[member]:
#                         members_to_experience[member][event] += 1
#                         score = emi.points_scored/c.total_points
#                         # members_to_skill_level[member][event] += weight * (score - discovered_experience_rate*(math.log(members_to_experience[member][event]))) + bias
#                         members_to_skill_level[member][event] += weight * (score - discovered_experience_rate*members_to_experience[member][event]) + bias
    
#     experience_rate = skill_data.experience_rate
#     for m in members_to_experience:
#         for e in members_to_experience[m]:
#             if members_to_experience[m][e]!=0:
#                 # members_to_skill_level[m][e] = (members_to_skill_level[m][e]/members_to_experience[m][e] - average_bias)/ average_weight + experience_rate*(math.log(members_to_experience[m][e]+1))
#                 members_to_skill_level[m][e] = (members_to_skill_level[m][e]/members_to_experience[m][e] - average_bias)/ average_weight + experience_rate*(members_to_experience[m][e]+1)
#     min_score = min([min([members_to_skill_level[m][e] for e in members_to_skill_level[m] if members_to_experience[m][e]>0], default = 0) for m in members_to_skill_level], default=0)
#     max_score = max([max([members_to_skill_level[m][e] for e in members_to_skill_level[m] if members_to_experience[m][e]>0], default = 1) for m in members_to_skill_level], default=1)
    
#     # scale members_to_skill_level to be between 0 and 1
#     for m in members_to_skill_level:
#         for e in available_events:
#             if members_to_experience[m][e]==0:
#                 members_to_skill_level[m][e] = 0
#             if max_score - min_score != 0:
#                 members_to_skill_level[m][e] = (members_to_skill_level[m][e] - min_score) / (max_score - min_score)
#             else:
#                 members_to_skill_level[m][e] = 0
#         members_to_skill_level[m]=dict(sorted(members_to_skill_level[m].items(), key=lambda item: item[1], reverse=True))


#     context = {
#         "id" : pk,
#         "required_members_on_events" : required_members_on_events,
#         "required_members" : required_members,
#         "seniors" : seniors,
#         "teams" : [t.team_size for t in teams],
#         "team_names" : [t.name for t in teams],
#         "members_to_ranked_preferences" : members_to_ranked_preferences,
#         "member_member_event_pairs" : json.dumps(member_member_event_pairs),
#         "generated_competition_settings" : generated_competition_settings,
#         "available_members" : available_members,
#         "available_events" : available_events,
#         "events_with_3_members" : events_with_3_members,
#         "build_events" : build_events,
#         "worst_preference_amount" : worst_preference_amount,
#         "members_to_skill_level" : members_to_skill_level,
#         "members_to_experience" : members_to_experience,
#         "conflicting_events" : conflicting_events,
#         "event_types" : event_types,
#         "min_score" : min_score,
#     }
#     return render(request, "generation/generation_frontend.html", context)


# ==================== EDIT PARTNER PREFERENCES ====================

@login_required
def editPartnerPreferencesView(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if generated_competition_settings.user.id != request.user.id:
        raise Http404

    member_queryset = AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings)
    event_queryset = AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)
    partner_prefs = WantedMemberMemberEventPair.objects.filter(member1__generated_competition_settings=generated_competition_settings)

    form = AddPartnerPreferenceForm(request.POST or None, member_queryset=member_queryset, event_queryset=event_queryset)

    if request.method == "POST":
        if form.is_valid():
            member1 = form.cleaned_data['member1']
            member2 = form.cleaned_data['member2']
            event = form.cleaned_data['event']
            # check for duplicate
            exists = WantedMemberMemberEventPair.objects.filter(
                member1=member1, member2=member2, event=event
            ).exists() or WantedMemberMemberEventPair.objects.filter(
                member1=member2, member2=member1, event=event
            ).exists()
            if exists:
                form.add_error(None, "This partner preference already exists.")
            else:
                WantedMemberMemberEventPair.objects.create(member1=member1, member2=member2, event=event)
                return redirect('editPartnerPreferencesView', pk=pk)

    context = {
        "form": form,
        "partner_prefs": partner_prefs,
        "generated_competition_settings": generated_competition_settings,
        "has_members": member_queryset.exists(),
    }
    return render(request, "generation/edit_partner_preferences.html", context)


@login_required
def deletePartnerPreference(request, pk):
    pref = get_object_or_404(WantedMemberMemberEventPair, id=pk)
    comp_pk = pref.member1.generated_competition_settings.id
    if pref.member1.generated_competition_settings.user.id == request.user.id:
        pref.delete()
        return redirect('editPartnerPreferencesView', pk=comp_pk)
    raise Http404


# ==================== EDIT EVENT CONFLICTS ====================

@login_required
def editConflictsView(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if generated_competition_settings.user.id != request.user.id:
        raise Http404

    events = AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)
    conflict_groups = ConflictingEvents.objects.filter(generated_competition_settings=generated_competition_settings)

    # events not in any conflict group
    unassigned_events = events.filter(conflict__isnull=True)

    # build conflict group data
    groups_data = []
    for cg in conflict_groups:
        cg_events = events.filter(conflict=cg)
        groups_data.append({
            "group": cg,
            "events": cg_events,
        })

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_group":
            ConflictingEvents.objects.create(generated_competition_settings=generated_competition_settings)
            return redirect('editConflictsView', pk=pk)
        elif action == "add_event_to_conflict":
            group_id = request.POST.get("group_id")
            event_id = request.POST.get("event_id")
            if group_id and event_id:
                event = get_object_or_404(AvailableEvent, id=event_id, generated_competition_settings=generated_competition_settings)
                group = get_object_or_404(ConflictingEvents, id=group_id, generated_competition_settings=generated_competition_settings)
                event.conflict = group
                event.save()
            return redirect('editConflictsView', pk=pk)

    context = {
        "generated_competition_settings": generated_competition_settings,
        "groups_data": groups_data,
        "unassigned_events": unassigned_events,
        "has_events": events.exists(),
    }
    return render(request, "generation/edit_conflicts.html", context)


@login_required
def removeEventFromConflict(request, pk):
    event = get_object_or_404(AvailableEvent, id=pk)
    comp_pk = event.generated_competition_settings.id
    if event.generated_competition_settings.user.id == request.user.id:
        event.conflict = None
        event.save()
        return redirect('editConflictsView', pk=comp_pk)
    raise Http404


@login_required
def deleteConflictGroup(request, pk):
    group = get_object_or_404(ConflictingEvents, id=pk)
    comp_pk = group.generated_competition_settings.id
    if group.generated_competition_settings.user.id == request.user.id:
        # events get conflict=None via SET_NULL cascade
        group.delete()
        return redirect('editConflictsView', pk=comp_pk)
    raise Http404


# ==================== EDIT EVENTS ====================

@login_required
def editEventsView(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if generated_competition_settings.user.id != request.user.id:
        raise Http404

    event_types = EventType.objects.filter(generated_competition_settings=generated_competition_settings)
    all_events = AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_event_type":
            existing_count = event_types.count()
            color = PASTEL_COLORS[existing_count % len(PASTEL_COLORS)]
            EventType.objects.create(generated_competition_settings=generated_competition_settings, color=color)
            return redirect('editEventsView', pk=pk)
        elif action == "change_color":
            et_id = request.POST.get("event_type_id")
            color_val = request.POST.get("color", "#FFE9D0")
            # convert from #RRGGBB to RRGGBB
            color_hex = color_val.lstrip("#").upper()
            if len(color_hex) == 6:
                et = get_object_or_404(EventType, id=et_id, generated_competition_settings=generated_competition_settings)
                et.color = color_hex
                et.save()
            return redirect('editEventsView', pk=pk)
        elif action == "add_event":
            et_id = request.POST.get("event_type_id")  # may be "none" for uncategorized
            event_name = request.POST.get("event_name", "").strip()
            needs_3 = request.POST.get("needs_3_members") == "on"
            is_build = request.POST.get("is_build_event") == "on"
            event_name = remove_punctuation(event_name, True)
            if event_name == "":
                # reload with error - we'll pass via GET param
                return redirect('editEventsView', pk=pk)
            # duplicate check
            if all_events.filter(name=event_name).exists():
                # we handle this via a simple redirect with error flag
                from django.contrib import messages
                messages.error(request, f'An event named "{event_name}" already exists.')
                return redirect('editEventsView', pk=pk)
            event_type = None
            if et_id and et_id != "none":
                event_type = get_object_or_404(EventType, id=et_id, generated_competition_settings=generated_competition_settings)
            AvailableEvent.objects.create(
                name=event_name,
                needs_3_members=needs_3,
                is_build_event=is_build,
                generated_competition_settings=generated_competition_settings,
                event_type=event_type,
            )
            return redirect('editEventsView', pk=pk)

    # build groups data
    groups_data = []
    for et in event_types:
        et_events = all_events.filter(event_type=et)
        groups_data.append({
            "event_type": et,
            "events": et_events,
            "color_hex": "#" + et.color,
        })

    uncategorized_events = all_events.filter(event_type__isnull=True)

    context = {
        "generated_competition_settings": generated_competition_settings,
        "groups_data": groups_data,
        "uncategorized_events": uncategorized_events,
        "has_any_events": all_events.exists() or event_types.exists(),
    }
    return render(request, "generation/edit_events.html", context)


@login_required
def deleteEvent(request, pk):
    event = get_object_or_404(AvailableEvent, id=pk)
    comp_pk = event.generated_competition_settings.id
    if event.generated_competition_settings.user.id == request.user.id:
        event.delete()
        return redirect('editEventsView', pk=comp_pk)
    raise Http404


@login_required
def deleteEventType(request, pk):
    et = get_object_or_404(EventType, id=pk)
    comp_pk = et.generated_competition_settings.id
    if et.generated_competition_settings.user.id == request.user.id:
        # events get event_type=None via SET_NULL
        et.delete()
        return redirect('editEventsView', pk=comp_pk)
    raise Http404


# ==================== EDIT PREFERENCES ====================

@login_required
def editPreferencesView(request, pk):
    generated_competition_settings = get_object_or_404(GeneratedCompetitionSettings, id=pk)
    if generated_competition_settings.user.id != request.user.id:
        raise Http404

    members = AvailableMember.objects.filter(generated_competition_settings=generated_competition_settings)
    all_events = AvailableEvent.objects.filter(generated_competition_settings=generated_competition_settings)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_member":
            member_name = request.POST.get("member_name", "").strip()
            is_senior = request.POST.get("is_senior") == "on"
            member_name = remove_punctuation(member_name, False)
            if member_name != "":
                if members.filter(name=member_name).exists():
                    from django.contrib import messages
                    messages.error(request, f'A member named "{member_name}" already exists.')
                else:
                    AvailableMember.objects.create(
                        generated_competition_settings=generated_competition_settings,
                        name=member_name,
                        is_senior=is_senior,
                    )
            return redirect('editPreferencesView', pk=pk)

        elif action == "add_preference":
            member_id = request.POST.get("member_id")
            event_id = request.POST.get("event_id")
            if member_id and event_id:
                member = get_object_or_404(AvailableMember, id=member_id, generated_competition_settings=generated_competition_settings)
                event = get_object_or_404(AvailableEvent, id=event_id, generated_competition_settings=generated_competition_settings)
                # check not already in preferences
                if not WantedMemberEventPair.objects.filter(member=member, event=event).exists():
                    max_rank = WantedMemberEventPair.objects.filter(member=member).order_by('-rank').values_list('rank', flat=True).first() or 0
                    WantedMemberEventPair.objects.create(rank=max_rank + 1, event=event, member=member)
            return redirect('editPreferencesView', pk=pk)

        elif action == "move_up":
            pref_id = request.POST.get("pref_id")
            pref = get_object_or_404(WantedMemberEventPair, id=pref_id)
            if pref.member.generated_competition_settings.id == int(pk):
                # find the preference with the next lower rank
                above = WantedMemberEventPair.objects.filter(member=pref.member, rank__lt=pref.rank).order_by('-rank').first()
                if above:
                    above.rank, pref.rank = pref.rank, above.rank
                    above.save()
                    pref.save()
            return redirect('editPreferencesView', pk=pk)

        elif action == "move_down":
            pref_id = request.POST.get("pref_id")
            pref = get_object_or_404(WantedMemberEventPair, id=pref_id)
            if pref.member.generated_competition_settings.id == int(pk):
                below = WantedMemberEventPair.objects.filter(member=pref.member, rank__gt=pref.rank).order_by('rank').first()
                if below:
                    below.rank, pref.rank = pref.rank, below.rank
                    below.save()
                    pref.save()
            return redirect('editPreferencesView', pk=pk)

    # build members data
    members_data = []
    for m in members:
        prefs = WantedMemberEventPair.objects.filter(member=m).order_by('rank')
        # events not already preferred by this member
        preferred_event_ids = prefs.values_list('event_id', flat=True)
        available = all_events.exclude(id__in=preferred_event_ids)
        members_data.append({
            "member": m,
            "preferences": prefs,
            "available_events": available,
        })

    context = {
        "generated_competition_settings": generated_competition_settings,
        "members_data": members_data,
        "has_members": members.exists(),
        "use_ranking": generated_competition_settings.use_ranking,
    }
    return render(request, "generation/edit_preferences.html", context)


@login_required
def deletePreference(request, pk):
    pref = get_object_or_404(WantedMemberEventPair, id=pk)
    member = pref.member
    comp_pk = member.generated_competition_settings.id
    if member.generated_competition_settings.user.id == request.user.id:
        deleted_rank = pref.rank
        pref.delete()
        # re-normalize ranks
        remaining = WantedMemberEventPair.objects.filter(member=member, rank__gt=deleted_rank)
        for p in remaining:
            p.rank -= 1
            p.save()
        return redirect('editPreferencesView', pk=comp_pk)
    raise Http404


@login_required
def deleteMember(request, pk):
    member = get_object_or_404(AvailableMember, id=pk)
    comp_pk = member.generated_competition_settings.id
    if member.generated_competition_settings.user.id == request.user.id:
        member.delete()
        return redirect('editPreferencesView', pk=comp_pk)
    raise Http404
