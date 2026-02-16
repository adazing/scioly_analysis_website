from django.shortcuts import render
import random
from .models import *
from .forms import *
from django.forms import ValidationError
from django.shortcuts import get_object_or_404, redirect
import string
import csv
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import numpy as np
import math
from django.db.models import Prefetch
from collections import defaultdict
import json
from html import escape as html_escape
import numpy as np
import math
from scipy.optimize import minimize
import statistics as stats_module
import time
from itertools import chain
from collections import defaultdict


# TODO: MAKE SURE THAT ONLY ALPHABET LETTERS ARE ALLOWED (NO PUNCTUATION THAT CAN CAUSE XSS ATTACKS)
def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces, then title-case
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.replace("(B)", "").replace("(3)", "").replace("&", "and") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)", "") if c.isalpha() or c==" "])
    return input_string.strip().title()

@login_required
def competitionView(request, pk):
    competition=get_object_or_404(Competition, id=pk)
    if competition.user.id==request.user.id:
        teams = Team.objects.filter(competition=competition)
        context = {
            "competition" : competition,
            "team_list" : teams,
        }
        return render(request, "data/competition_view.html", context)
    raise Http404

@login_required
def competitionCreateView(request):
    form = CompetitionForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            competition = Competition.objects.create(name=form.cleaned_data.get("name"),user=request.user, date=form.cleaned_data.get("date"), number_of_teams_competed=form.cleaned_data.get("number_of_teams_competed"))
            return redirect("competitionView", pk=competition.id)
    context = {
        'form':form,
    }
    return render(request, 'data/competition_write.html', context)

@login_required
def practiceCreateView(request):
    form = PracticeForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            event = remove_punctuation(form.cleaned_data.get("event_name"), True)
            name = form.cleaned_data.get("name", "").strip()
            practice = Practice.objects.create(name=name, event_name=event, user=request.user, date=form.cleaned_data.get("date"), total_points=form.cleaned_data.get("total_points"))
            score_data = form.cleaned_data.get("score_data")
            if score_data is not None:
                reader = csv.reader(score_data.splitlines(), delimiter=',')
                for row in reader:
                    if len(row) < 2:
                        continue
                    member_name = row[0]
                    member_name = remove_punctuation(member_name, False)
                    points = float(row[1])
                    if member_name!="":
                        EventMemberPracticeInstance.objects.create(practice=practice, member_name=member_name, points_scored=points)
                    else:
                        break
            return redirect("practiceView", pk=practice.id)
    context = {
        'form':form,
    }
    return render(request, 'data/practice_write.html', context)

@login_required
def practiceEditView(request, pk):
    practice = get_object_or_404(Practice, id=pk)
    if practice.user != request.user:
        raise Http404
    form = PracticeEditForm(request.POST or None, instance=practice)
    if request.method == "POST":
        if form.is_valid():
            event = remove_punctuation(form.cleaned_data.get("event_name"), True)
            date = form.cleaned_data.get("date")
            total_points=form.cleaned_data.get("total_points")
            name = form.cleaned_data.get("name", "").strip()
            practice.name=name
            practice.event_name=event
            practice.date=date
            practice.total_points=total_points
            practice.save()
            return redirect("practiceView", pk=practice.id)
    context = {
        'form':form,
        'practice':practice,
    }
    return render(request, 'data/practice_write.html', context)


@login_required
def practiceView(request, pk):
    practice=get_object_or_404(Practice, id=pk)
    if practice.user.id == request.user.id:
        results=[]
        event_member_instance_list = EventMemberPracticeInstance.objects.filter(practice=practice)
        for e_m_i in event_member_instance_list:
            result=[]
            result.append(e_m_i.member_name)
            score_color=max(0,min(1, 1-e_m_i.points_scored/practice.total_points))*100
            text_color = '#FFF' if score_color<35 else "#000"
            result.append(str(e_m_i.points_scored))
            result.append((score_color, text_color))
            results.append(result)

        # Analysis
        analysis = None
        if event_member_instance_list.exists():
            scores = [e.points_scored for e in event_member_instance_list]
            total = practice.total_points
            sorted_scores = sorted(scores)
            avg_score = round(sum(scores) / len(scores), 1)
            avg_pct = round(avg_score / total * 100, 1) if total > 0 else 0

            if len(sorted_scores) >= 2:
                quartiles = stats_module.quantiles(sorted_scores, n=4)
                p25 = round(quartiles[0], 1)
                p50 = round(stats_module.median(sorted_scores), 1)
                p75 = round(quartiles[2], 1)
            else:
                p25 = p50 = p75 = sorted_scores[0]

            members = []
            for e in event_member_instance_list:
                pct = round(e.points_scored / total * 100, 1) if total > 0 else 0
                if e.points_scored >= p75:
                    highlight = "Top quartile"
                    badge = "success"
                elif e.points_scored >= p50:
                    highlight = "Above median"
                    badge = "primary"
                elif e.points_scored >= p25:
                    highlight = "Below median"
                    badge = "warning"
                else:
                    highlight = "Bottom quartile"
                    badge = "danger"
                members.append({
                    'name': e.member_name, 'score': e.points_scored,
                    'pct': pct, 'highlight': highlight, 'badge': badge,
                })
            members.sort(key=lambda x: x['score'], reverse=True)

            analysis = {
                'avg_score': avg_score, 'avg_pct': avg_pct,
                'p25': p25, 'p50': p50, 'p75': p75,
                'num_members': len(scores),
                'members': members,
            }

        context = {
            "practice" : practice,
            "results" : results,
            "analysis" : analysis,
        }
        return render(request, "data/practice_view.html", context)
    raise Http404

@login_required
def practiceDeleteView(request, pk):
    practice = get_object_or_404(Practice, id=pk)
    if practice.user.id == request.user.id:
        form = DeleteConfirmationForm(request.POST or None)
        context = {
            "item": practice.name,
            "form":form,
            "practice":practice,
        }
        if request.method=="POST" and form.is_valid():
            practice.delete()
            return redirect("competitionListView")
        return render(request, 'data/confirm_delete.html', context)
    raise Http404

@login_required
def competitionEditView(request, pk):
    competition = get_object_or_404(Competition, id=pk)
    if competition.user.id == request.user.id:
        form = CompetitionForm(request.POST or None, instance=competition)
        if request.method == "POST" and form.is_valid():
            competition.name=form.cleaned_data.get("name")
            competition.date=form.cleaned_data.get("date")
            competition.number_of_teams_competed=form.cleaned_data.get("number_of_teams_competed")
            competition.save()
            return redirect("competitionView", pk=competition.id)
        context = {
            "form":form,
            "competition":competition,
        }
        return render(request, 'data/competition_write.html', context)
    raise Http404

@login_required
def competitionDeleteView(request, pk):
    competition = get_object_or_404(Competition, id=pk)
    if competition.user.id == request.user.id:
        form = DeleteConfirmationForm(request.POST or None)
        context = {
            "item":"competition "+competition.name,
            "form":form,
            "competition":competition,
        }
        if request.method=="POST" and form.is_valid():
            competition.delete()
            return redirect("competitionListView")
        return render(request, 'data/confirm_delete.html', context)
    raise Http404

# Create event member instances based on CSV file. (Upload the team scores
# [with individual scores and stuff]
# in CSV file, convert that into to real instances [into the real model, so it's processing that file so don't
# have to keep reading that file so it's processing and storing it])
@login_required
def teamCreateView(request, pk):
    form = TeamForm(request.POST or None, request.FILES or None)
    competition = get_object_or_404(Competition, id=pk)
    if competition.user.id == request.user.id:
        if request.method == "POST":
            if form.is_valid():
                team_name = form.cleaned_data["name"]
                team = Team.objects.create(name=team_name, competition=competition)
                score_data = form.cleaned_data.get("score_data")
                if score_data is not None:
                    reader = csv.reader(score_data.splitlines(), delimiter=',')
                    for row in reader:
                        if len(row) < 5:
                            continue
                        event_name=row[0]
                        event_name = remove_punctuation(event_name, True)
                        score = int(row[4])
                        if event_name!="":
                            event_member_instance = EventMemberInstance.objects.create(event_name=event_name, team=team, score=score)
                            for m in range(1,4):
                                member_name = remove_punctuation(row[m], False)
                                if member_name!="":
                                    Member.objects.create(name=member_name, event_member_instance=event_member_instance)
                        else: # reached end
                            break
                return redirect("teamView", pk=team.id)
                
        context={
            "form":form,
            "competition":competition,
        }
        return render(request, 'data/team_write.html', context)
    raise Http404

@login_required
def teamDeleteView(request, pk):
    team = get_object_or_404(Team, id=pk)
    if team.competition.user.id == request.user.id:
        form = DeleteConfirmationForm(request.POST or None)
        context = {
            "item":"Team "+team.name,
            "form":form,
            "team":team,
        }
        if request.method=="POST" and form.is_valid():
            team.delete()
            return redirect("competitionView", pk=team.competition.id)
        return render(request, 'data/confirm_delete.html', context)
    raise Http404

@login_required
def editTeamResultsView(request, pk):
    team = get_object_or_404(Team, id=pk)
    if team.competition.user.id != request.user.id:
        raise Http404
    error = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_team":
            new_name = request.POST.get("team_name", "").strip()
            new_notes = request.POST.get("team_notes", "").strip()
            if new_name:
                team.name = new_name
                team.notes = new_notes
                team.save()
            else:
                error = "Team name cannot be empty."
            if not error:
                return redirect("editTeamResultsView", pk=team.id)
        elif action == "add_event":
            event_name = remove_punctuation(request.POST.get("event_name", ""), True)
            member1 = remove_punctuation(request.POST.get("member1", ""), False)
            member2 = remove_punctuation(request.POST.get("member2", ""), False)
            member3 = remove_punctuation(request.POST.get("member3", ""), False)
            score_str = request.POST.get("score", "").strip()
            if not event_name:
                error = "Event name is required."
            elif not member1:
                error = "At least one member is required."
            elif EventMemberInstance.objects.filter(team=team, event_name=event_name).exists():
                error = "An event with that name already exists for this team."
            else:
                try:
                    score = int(score_str)
                    if score < 1:
                        error = "Score must be a positive integer."
                except (ValueError, TypeError):
                    error = "Score must be a positive integer."
            if not error:
                emi = EventMemberInstance.objects.create(event_name=event_name, team=team, score=score)
                for name in [member1, member2, member3]:
                    if name:
                        Member.objects.create(name=name, event_member_instance=emi)
                return redirect("editTeamResultsView", pk=team.id)
        elif action == "edit_score":
            emi_id = request.POST.get("emi_id")
            emi = get_object_or_404(EventMemberInstance, id=emi_id, team=team)
            new_score_str = request.POST.get("score", "").strip()
            member1 = remove_punctuation(request.POST.get("member1", ""), False)
            member2 = remove_punctuation(request.POST.get("member2", ""), False)
            member3 = remove_punctuation(request.POST.get("member3", ""), False)
            if not member1:
                error = "At least one member is required."
            else:
                try:
                    new_score = int(new_score_str)
                    if new_score < 1:
                        error = "Score must be a positive integer."
                except (ValueError, TypeError):
                    error = "Score must be a positive integer."
            if not error:
                emi.score = new_score
                emi.save()
                Member.objects.filter(event_member_instance=emi).delete()
                for name in [member1, member2, member3]:
                    if name:
                        Member.objects.create(name=name, event_member_instance=emi)
                return redirect("editTeamResultsView", pk=team.id)

    event_results = []
    for emi in EventMemberInstance.objects.filter(team=team):
        members = list(Member.objects.filter(event_member_instance=emi))
        member_names = [m.name for m in members]
        while len(member_names) < 3:
            member_names.append("")
        event_results.append({
            "id": emi.id,
            "event_name": emi.event_name,
            "member1": member_names[0],
            "member2": member_names[1],
            "member3": member_names[2],
            "score": emi.score,
        })
    context = {
        "team": team,
        "event_results": event_results,
        "error": error,
    }
    return render(request, "data/edit_team_results.html", context)


@login_required
def deleteEventMemberInstance(request, pk):
    emi = get_object_or_404(EventMemberInstance, id=pk)
    team = emi.team
    if team.competition.user.id != request.user.id:
        raise Http404
    if request.method == "POST":
        emi.delete()
    return redirect("editTeamResultsView", pk=team.id)


@login_required
def editPracticeResultsView(request, pk):
    practice = get_object_or_404(Practice, id=pk)
    if practice.user.id != request.user.id:
        raise Http404
    error = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_result":
            member_name = remove_punctuation(request.POST.get("member_name", ""), False)
            points_str = request.POST.get("points_scored", "").strip()
            if not member_name:
                error = "Member name is required."
            elif EventMemberPracticeInstance.objects.filter(practice=practice, member_name=member_name).exists():
                error = "A result for that member already exists."
            else:
                try:
                    points = float(points_str)
                    if points < 0:
                        error = "Points must be non-negative."
                except (ValueError, TypeError):
                    error = "Points must be a valid number."
            if not error:
                EventMemberPracticeInstance.objects.create(practice=practice, member_name=member_name, points_scored=points)
                return redirect("editPracticeResultsView", pk=practice.id)
        elif action == "edit_result":
            empi_id = request.POST.get("empi_id")
            empi = get_object_or_404(EventMemberPracticeInstance, id=empi_id, practice=practice)
            member_name = remove_punctuation(request.POST.get("member_name", ""), False)
            points_str = request.POST.get("points_scored", "").strip()
            if not member_name:
                error = "Member name is required."
            else:
                try:
                    points = float(points_str)
                    if points < 0:
                        error = "Points must be non-negative."
                except (ValueError, TypeError):
                    error = "Points must be a valid number."
            if not error:
                empi.member_name = member_name
                empi.points_scored = points
                empi.save()
                return redirect("editPracticeResultsView", pk=practice.id)

    results = []
    for empi in EventMemberPracticeInstance.objects.filter(practice=practice):
        results.append({
            "id": empi.id,
            "member_name": empi.member_name,
            "points_scored": empi.points_scored,
        })
    context = {
        "practice": practice,
        "results": results,
        "error": error,
    }
    return render(request, "data/edit_practice_results.html", context)


@login_required
def deletePracticeResult(request, pk):
    empi = get_object_or_404(EventMemberPracticeInstance, id=pk)
    practice = empi.practice
    if practice.user.id != request.user.id:
        raise Http404
    if request.method == "POST":
        empi.delete()
    return redirect("editPracticeResultsView", pk=practice.id)


@login_required
def teamView(request, pk):
    team=get_object_or_404(Team, id=pk)
    if team.competition.user.id == request.user.id:
        results=[]
        event_member_instance_list = EventMemberInstance.objects.filter(team=team)
        results2 = {}
        for e_m_i in event_member_instance_list:
            result=[]
            result.append(e_m_i.event_name)
            member_list = Member.objects.filter(event_member_instance=e_m_i)
            score_color=max(0,min(1, e_m_i.score/team.competition.number_of_teams_competed))*100
            text_color = '#FFF' if score_color<35 else "#000"
            for x in range(3):
                if x>=len(member_list):
                    result.append("")
                else:
                    result.append(member_list[x].name)
                    if member_list[x].name in results2:
                        results2[member_list[x].name].append((e_m_i.event_name+" ("+str(e_m_i.score)+")",score_color,text_color))
                    else:
                        results2[member_list[x].name]=[(e_m_i.event_name+" ("+str(e_m_i.score)+")",score_color,text_color)]
            result.append(str(e_m_i.score))
            result.append((score_color, text_color))
            results.append(result)
        
        max_events_per_member = max([len(results2[m]) for m in results2], default=0)
        for member in results2:
            results2[member] += [('', 100.0, '#000') for i in range(max_events_per_member-len(results2[member]))]

        # Analysis
        analysis = None
        num_teams = team.competition.number_of_teams_competed
        all_scores = [emi.score for emi in event_member_instance_list]
        non_dq_scores = [s for s in all_scores if s <= num_teams]
        emi_members = {}
        for emi in event_member_instance_list:
            emi_members[emi.id] = ', '.join(m.name for m in Member.objects.filter(event_member_instance=emi))

        dq_events = [{'event': emi.event_name, 'members': emi_members.get(emi.id, '')}
                     for emi in event_member_instance_list if emi.score > num_teams]

        if non_dq_scores:
            sorted_scores = sorted(non_dq_scores)
            avg_placement = round(sum(non_dq_scores) / len(non_dq_scores), 1)
            if len(sorted_scores) >= 2:
                quartiles = stats_module.quantiles(sorted_scores, n=4)
                p25 = round(quartiles[0], 1)
                p50 = round(stats_module.median(sorted_scores), 1)
                p75 = round(quartiles[2], 1)
            else:
                p25 = p50 = p75 = sorted_scores[0]

            best_events = [{'event': emi.event_name, 'score': emi.score, 'members': emi_members.get(emi.id, '')}
                           for emi in event_member_instance_list
                           if emi.score <= num_teams and emi.score <= p25]
            best_events.sort(key=lambda x: x['score'])

            worst_events = [{'event': emi.event_name, 'score': emi.score, 'members': emi_members.get(emi.id, '')}
                            for emi in event_member_instance_list
                            if emi.score <= num_teams and emi.score >= p75]
            worst_events.sort(key=lambda x: x['score'], reverse=True)

            member_scores = defaultdict(list)
            for emi in event_member_instance_list:
                if emi.score <= num_teams:
                    for m in Member.objects.filter(event_member_instance=emi):
                        member_scores[m.name].append(emi.score)

            member_avgs = []
            for name, m_scores in member_scores.items():
                m_avg = round(sum(m_scores) / len(m_scores), 1)
                if m_avg <= p25:
                    highlight = "Top quartile"
                    badge = "success"
                elif m_avg <= p50:
                    highlight = "Above median"
                    badge = "primary"
                elif m_avg <= p75:
                    highlight = "Below median"
                    badge = "warning"
                else:
                    highlight = "Bottom quartile"
                    badge = "danger"
                member_avgs.append({
                    'name': name, 'avg': m_avg,
                    'num_events': len(m_scores),
                    'highlight': highlight, 'badge': badge,
                })
            member_avgs.sort(key=lambda x: x['avg'])

            analysis = {
                'avg_placement': avg_placement,
                'p25': p25, 'p50': p50, 'p75': p75,
                'num_events': len(all_scores),
                'num_events_non_dq': len(non_dq_scores),
                'total_score': sum(all_scores),
                'dq_count': len(dq_events),
                'dq_events': dq_events,
                'best_events': best_events,
                'worst_events': worst_events,
                'members': member_avgs,
            }

        context = {
            "team" : team,
            "results" : results,
            "results2" : results2,
            "max_events_per_member" : range(1, max_events_per_member+1),
            "analysis" : analysis,
        }
        return render(request, "data/team_view.html", context)
    raise Http404


@login_required
def competitionListView(request):
    competitions = Competition.objects.filter(user=request.user.id).order_by('-date')
    practices = Practice.objects.filter(user=request.user).order_by('-date')
    context = {
        "competition_list":competitions,
        "practice_list": practices,
    }
    return render(request, "data/competition_list.html", context)


@login_required
def skillView2(request):
    if not SkillData.objects.filter(user=request.user).exists():
        SkillData.objects.create(user=request.user)
    skill_data = SkillData.objects.get(user=request.user)
    form = SkillDataForm(request.POST or None, instance=skill_data)
    if request.method == "POST" and form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        experience_rate = form.cleaned_data.get("experience_rate")
        use_initial_skill = form.cleaned_data.get("use_initial_skill")
        include_disqualifications = form.cleaned_data.get("include_disqualifications")
        user = request.user
        SkillData.objects.filter(user=user).delete()
        SkillData.objects.create(start_date = start_date, end_date = end_date, experience_rate = experience_rate, use_initial_skill = use_initial_skill, include_disqualifications = include_disqualifications, user = user)
    skill_data = SkillData.objects.get(user=request.user)
    
    # looking through data
    competition_list = Competition.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of competitions
    practice_list = Practice.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of practice instances
    instance_to_emis = dict() # dictionary that maps competitions or practice tests to dictionary that pairs (event, member) to observed skill
    instance_to_emi_data = dict()
    include_dq = skill_data.include_disqualifications
    me_to_skill = defaultdict(list)
    # Bulk-fetch all competition EMIs with members in 2 queries instead of N+1
    all_comp_emis = EventMemberInstance.objects.filter(
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
    all_practice_emis = EventMemberPracticeInstance.objects.filter(
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
    # deal with instances with no matches

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
    
    # recompute everything
    members_to_skill_level = dict()
    members_to_experience = dict()
    members_to_data = dict()
    all_events=set()
    
    skill_no_exp = new_params[-1]
    for member_lower, event_lower in me_to_skill: # for each member, event pair
        instances = me_to_skill[(member_lower, event_lower)] # instance where member, event pair competed
        member = member_lower.title()
        event = event_lower.title()
        all_events.add(event)
        num_scores = len(instances) # num instances where member, event pair competed
        scores = dict()
        sum_scores = 0
        if member in members_to_skill_level:
            members_to_data[member][event] = "<ul style='padding:0;  margin-top:10px; margin-bottom:0;'>"
        else:
            members_to_data[member] = {event:"<ul style='padding:0;  margin-top:10px; margin-bottom:0;'>"}
            members_to_experience[member] = {event:0}
            members_to_skill_level[member] = {event:0}
        for i in instances: # compute final scores
            instance_idx = instance_to_idx[i]
            emi = instance_to_emi_data[i][(member_lower, event_lower)]
            score = instance_to_emis[i][(member_lower, event_lower)]
            weight = new_params[instance_idx*2]
            bias = new_params[instance_idx*2+1]
            final_score = weight * score + bias
            scores[i]=final_score
            sum_scores += final_score
            if i in competition_list: # instance is a competition
                members_to_data[member][event] += "<li>"+html_escape(i.name)+" "+html_escape(emi.team.name)+": ranked "+str(emi.score)+"/"+str(i.number_of_teams_competed)+" in "+html_escape(emi.event_name.title())+"</li>"
            else: # instance is a practice test
                members_to_data[member][event] += "<li>Practice "+html_escape(i.event_name.title())+": scored "+str(emi.points_scored)+"/"+str(i.total_points)+"</li>"
        # compute predicted scores
        pred_final_score = sum_scores / num_scores
        pred_score = (pred_final_score - average_bias) / average_weight + skill_data.experience_rate*num_scores
        members_to_skill_level[member][event] = pred_score
        members_to_experience[member][event] = num_scores

    all_events = sorted(list(all_events))
    
    for m in members_to_experience:
        for e in all_events:
            if e not in members_to_experience[m]:
                members_to_experience[m][e] = 0
                # members_to_data[m][e] = "<p>No Data</p>"
                members_to_skill_level[m][e] = skill_no_exp if use_initial_skill else 0

    min_score = min([min(members_to_skill_level[m].values(), default = 0) for m in members_to_skill_level], default=0)
    max_score = max([max(members_to_skill_level[m].values(), default = 1) for m in members_to_skill_level], default=1)
    
    
    table_columns = ["Name"]+all_events
    max_xp = max([max(members_to_experience[m].values(), default=0) for m in members_to_experience], default=0)
    table_info_data = [["".join([members_to_data[m][e]+"</ul>" for e in members_to_data[m]])]+[members_to_data[m][e]+"</ul>" if members_to_experience[m][e]>0 else "<p>No Data</p>" for e in all_events] for m in members_to_skill_level]
    table_skill_data = [[m]+[round((members_to_skill_level[m][e]-min_score)*100/(max_score-min_score), 2) if e in members_to_skill_level[m] else 0 for e in all_events] for m in members_to_skill_level]
    table_xp_data = [[m]+[members_to_experience[m][e] if e in members_to_experience[m] else 0 for e in all_events] for m in members_to_experience]

    # Build Tabulator data as proper JSON
    tabledata = []
    for t in range(len(table_skill_data)):
        row = {}
        for i in range(len(table_columns)):
            row[table_columns[i]] = table_skill_data[t][i]
            row[table_columns[i]+"_INFO"] = table_info_data[t][i]
        tabledata.append(row)
    table_data = "var tabledata = " + json.dumps(tabledata) + ";"

    tabledata2 = []
    for t in range(len(table_xp_data)):
        row = {}
        for i in range(len(table_columns)):
            row[table_columns[i]] = table_xp_data[t][i]
            row[table_columns[i]+"_INFO"] = table_info_data[t][i]
        tabledata2.append(row)
    table_data2 = "var tabledata2 = " + json.dumps(tabledata2) + ";"

    context = {
        "max_xp":max_xp,
        "event_list":all_events,
        "table_data":table_data,
        "table_data2":table_data2,
        "form": form,
    }
    return render(request, "data/skill_view.html", context)


@login_required
def nameChange(request):
    
    member_names = set()
    for m in Member.objects.filter(event_member_instance__team__competition__user=request.user).values_list('name', flat=True).distinct():
        member_names.add(m.lower())
    for m in EventMemberPracticeInstance.objects.filter(practice__user=request.user).values_list('member_name', flat=True).distinct():
        member_names.add(m.lower())
    member_queryset = tuple([('', "-----")] + sorted([(m.title(), m.title()) for m in member_names]))
    event_names = set()
    for e in EventMemberInstance.objects.filter(team__competition__user=request.user).values_list('event_name', flat=True).distinct():
        event_names.add(e.lower())
    for e in Practice.objects.filter(user=request.user).values_list("event_name", flat=True).distinct():
        event_names.add(e.lower())
    event_queryset = tuple([('', "-----")] + sorted([(e.title(), e.title()) for e in event_names]))

    form = NameChangeForm(request.POST or None, member_queryset=member_queryset, event_queryset=event_queryset)
    
    if request.method == "POST":
        if form.is_valid():
            member = form.cleaned_data.get("member")
            event = form.cleaned_data.get("event")
            name = form.cleaned_data.get("name")

            if member:  # Update member name
                new_name = remove_punctuation(name, False)
                Member.objects.filter(event_member_instance__team__competition__user=request.user, name__iexact=member).update(name=new_name)
                EventMemberPracticeInstance.objects.filter(practice__user=request.user, member_name__iexact=member).update(member_name=new_name)

            if event:  # Update event name
                new_name = remove_punctuation(name, True)
                EventMemberInstance.objects.filter(event_name__iexact=event, team__competition__user=request.user).update(event_name=new_name)
                Practice.objects.filter(user=request.user, event_name__iexact=event).update(event_name=new_name)

            return redirect("competitionListView")
    
    context = {
        "form": form,
    }
    return render(request, "data/name_change.html", context)
