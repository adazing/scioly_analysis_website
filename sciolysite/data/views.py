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
import numpy as np
import math
from scipy.optimize import minimize
import time
from itertools import chain


# TODO: MAKE SURE THAT ONLY ALPHABET LETTERS ARE ALLOWED (NO PUNCTUATION THAT CAN CAUSE XSS ATTACKS)
def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.replace("(B)", "").replace("(3)", "").lower().replace("&", "and") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)", "").lower() if c.isalpha() or c==" "])
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
            practice = Practice.objects.create(event_name=event, user=request.user, date=form.cleaned_data.get("date"), total_points=form.cleaned_data.get("total_points"))
            reader = csv.reader(form.cleaned_data.get("score_data").splitlines(), delimiter=',')
            for row in reader:
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
            practice.event_name=event
            practice.date=date
            practice.total_points=total_points
            practice.save()
            return redirect("practiceView", pk=practice.id)
    context = {
        'form':form,
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
                
        context = {
            "practice" : practice,
            "results" : results,
        }
        return render(request, "data/practice_view.html", context)
    raise Http404

@login_required
def practiceDeleteView(request, pk):
    practice = get_object_or_404(Practice, id=pk)
    if practice.user.id == request.user.id:
        form = DeleteConfirmationForm(request.POST or None)
        context = {
            "item":"Practice "+practice.event_name,
            "form":form,
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
                reader = csv.reader(form.cleaned_data.get("score_data").splitlines(), delimiter=',')
                team = Team.objects.create(name=team_name, competition=competition)
                for row in reader:
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
        }
        if request.method=="POST" and form.is_valid():
            team.delete()
            return redirect("competitionView", pk=team.competition.id)
        return render(request, 'data/confirm_delete.html', context)
    raise Http404

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
        
        max_events_per_member = max([len(results2[m]) for m in results2])
        for member in results2:
            results2[member] += [('', 100.0, '#000') for i in range(max_events_per_member-len(results2[member]))]
        
        context = {
            "team" : team,
            "results" : results,
            "results2" : results2,
            "max_events_per_member" : range(1, max_events_per_member+1),
        }
        return render(request, "data/team_view.html", context)
    raise Http404


@login_required
def competitionListView(request):
    competitions = Competition.objects.filter(user=request.user.id)
    practices = Practice.objects.filter(user=request.user)
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
        user = request.user
        SkillData.objects.filter(user=user).delete()
        SkillData.objects.create(start_date = start_date, end_date = end_date, experience_rate = experience_rate, user = user)
    skill_data = SkillData.objects.get(user=request.user)
    competition_list = Competition.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of competitions
    practice_list = Practice.objects.filter(user=request.user, date__gte=skill_data.start_date, date__lte=skill_data.end_date).order_by('date') # list of practice instances
    competition_to_emis = {} # dictionary that maps competitions to dictionary that pairs (event, member) to quartile
    for c in competition_list: # for all the competitions
        emis_list = EventMemberInstance.objects.filter(team__competition=c) # get all the events
        results_dict = dict()
        for emi in emis_list: # for each of the events
            members = [m.name for m in Member.objects.filter(event_member_instance = emi)] # get all the members in event
            for m in members: # for each member on the event
                if emi.score < c.number_of_teams_competed: # if the scores is less than the number of teams that competed
                    results_dict[(emi.event_name, m)] = 1-emi.score/c.number_of_teams_competed
        if results_dict:
            competition_to_emis[c] = results_dict
    for p in practice_list:
        emis_list = EventMemberPracticeInstance.objects.filter(practice=p)
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
    
    discovered_experience_rate = abs(new_params[-2])
    
    members_to_skill_level = dict()
    members_to_experience = dict()
    members_to_data = dict()
    all_events=set()
    for c_idx in range(num_competitions):
        c = all_list[c_idx]
        if c in competition_list:
            emis_list = EventMemberInstance.objects.filter(team__competition=c)
            school_scores_of_competition = [x.score for x in EventMemberInstance.objects.filter(team__competition=c) if x.score<=x.team.competition.number_of_teams_competed]
            if len(school_scores_of_competition) != 0:
                for emi in emis_list:
                    all_events.add(emi.event_name)
                    if emi.score < c.number_of_teams_competed:
                        weight = abs(new_params[c_idx*2])
                        bias = new_params[c_idx*2+1]
                        event = emi.event_name
                        members = [m.name for m in Member.objects.filter(event_member_instance = emi)]
                        
                        for m in members:
                            if m in members_to_experience:
                                if event in members_to_experience[m]:
                                    members_to_experience[m][event] += 1
                                    members_to_data[m][event] += "<li>"+c.name+" "+emi.team.name+": ranked "+str(emi.score)+"/"+str(c.number_of_teams_competed)+" in "+emi.event_name+"</li>"
                                else:
                                    members_to_experience[m][event] = 1
                                    members_to_skill_level[m][event] = 0
                                    members_to_data[m][event] = "<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+c.name+" "+emi.team.name+": ranked "+str(emi.score)+"/"+str(c.number_of_teams_competed)+" in "+emi.event_name+"</li>"
                            else:
                                members_to_experience[m] = {}
                                members_to_data[m] = {}
                                members_to_skill_level[m] = {}
                                members_to_skill_level[m][event] = 0
                                members_to_data[m][event] = "<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+c.name+" "+emi.team.name+": ranked "+str(emi.score)+"/"+str(c.number_of_teams_competed)+" in "+emi.event_name+"</li>"
                                members_to_experience[m][event] = 1
                        score = 1-(emi.score/c.number_of_teams_competed)
                        for m in members:
                            members_to_skill_level[m][event] += weight * (score - discovered_experience_rate*(math.log(members_to_experience[m][event]))) + bias
        else:
            emis_list = EventMemberPracticeInstance.objects.filter(practice=c)
            for emi in emis_list:
                all_events.add(emi.practice.event_name)
                weight = abs(new_params[c_idx*2])
                bias = new_params[c_idx*2+1]
                event = emi.practice.event_name
                member = emi.member_name
                
                if member in members_to_experience:
                    if event in members_to_experience[member]:
                        members_to_experience[member][event] += 1
                        members_to_data[member][event] += "<li>Practice "+p.event_name+": scored "+str(emi.points_scored)+"/"+str(c.total_points)+"</li>"
                    else:
                        members_to_experience[member][event] = 1
                        members_to_skill_level[member][event] = 0
                        members_to_data[member][event] = "<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>Practice "+c.event_name+": scored "+str(emi.points_scored)+"/"+str(c.total_points)+"</li>"
                else:
                    members_to_experience[member] = {}
                    members_to_data[member] = {}
                    members_to_skill_level[member] = {}
                    members_to_skill_level[member][event] = 0
                    members_to_data[member][event] = "<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>Practice "+c.event_name+": scored "+str(emi.points_scored)+"/"+str(c.total_points)+"</li>"
                    members_to_experience[member][event] = 1
                score = emi.points_scored/c.total_points
                members_to_skill_level[member][event] += weight * (score - discovered_experience_rate*(math.log(members_to_experience[member][event]))) + bias
    experience_rate = skill_data.experience_rate
    for m in members_to_experience:
        for e in members_to_experience[m]:
            members_to_skill_level[m][e] = (members_to_skill_level[m][e]/members_to_experience[m][e] - average_bias)/ average_weight + experience_rate*(math.log(members_to_experience[m][e]+1))

    min_score = min([min(members_to_skill_level[m].values(), default = 0) for m in members_to_skill_level], default=0)
    max_score = max([max(members_to_skill_level[m].values(), default = 1) for m in members_to_skill_level], default=1)
    
    all_events = sorted(list(all_events))
    table_columns = ["Name"]+all_events
    max_xp = max([max(members_to_experience[m].values(), default=0) for m in members_to_experience], default=0)
    
    table_info_data = [["".join([members_to_data[m][e]+"</ul>" for e in members_to_skill_level[m]])]+[members_to_data[m][e]+"</ul>" if e in members_to_skill_level[m] else "<p>No Data</p>" for e in all_events] for m in members_to_skill_level]
    table_data = [[m]+[round((members_to_skill_level[m][e]-min_score)*100/(max_score-min_score), 2) if e in members_to_skill_level[m] else 0 for e in all_events] for m in members_to_skill_level]
    table_data = [table_data, table_info_data]
    table_data = "var tabledata = ["+"".join(["{"+"".join(['"'+str(table_columns[i])+'":'+str(table_data[0][t][i])+','+'"'+str(table_columns[i])+'_INFO":"'+str(table_data[1][t][i])+'",' if i!=0 else '"'+str(table_columns[i])+'":"'+str(table_data[0][t][i])+'",'+'"'+str(table_columns[i])+'_INFO":"'+str(table_data[1][t][i])+'",' for i in range(len(table_columns))])+"}," for t in range(len(table_data[0]))])+"];"

    table_data2 = [[m]+[members_to_experience[m][e] if e in members_to_experience[m] else 0 for e in all_events] for m in members_to_experience]
    table_data2 = [table_data2, table_info_data]
    table_data2 = "var tabledata2 = ["+"".join(["{"+"".join(['"'+str(table_columns[i])+'":'+str(table_data2[0][t][i])+','+'"'+str(table_columns[i])+'_INFO":"'+str(table_data2[1][t][i])+'",' if i!=0 else '"'+str(table_columns[i])+'":"'+str(table_data2[0][t][i])+'",'+'"'+str(table_columns[i])+'_INFO":"'+str(table_data2[1][t][i])+'",' for i in range(len(table_columns))])+"}," for t in range(len(table_data2[0]))])+"];"

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
    
    member_queryset = {(m, m) for m in Member.objects.filter(event_member_instance__team__competition__user=request.user).values_list('name', flat=True).distinct()}
    member_queryset.update({(m, m) for m in EventMemberPracticeInstance.objects.filter(practice__user=request.user).values_list('member_name', flat=True).distinct()})
    # member_queryset = list(chain(member_queryset, EventMemberPracticeInstance.objects.filter(practice__user=request.user).values_list('member_name', flat=True).distinct()))
    member_queryset = tuple([('', "-----")] + sorted(list(member_queryset)))
    event_queryset = {(e, e) for e in EventMemberInstance.objects.filter(team__competition__user=request.user).values_list('event_name', flat=True).distinct()}
    event_queryset.update({(e, e) for e in Practice.objects.filter(user=request.user).values_list("event_name", flat=True).distinct()})
    event_queryset = tuple([('', "-----")] + sorted(list(event_queryset)))

    form = NameChangeForm(request.POST or None, member_queryset=member_queryset, event_queryset=event_queryset)
    
    if request.method == "POST":
        if form.is_valid():
            member = form.cleaned_data.get("member")
            event = form.cleaned_data.get("event")
            name = form.cleaned_data.get("name")

            if member:  # Update member name
                new_name = remove_punctuation(name, False)
                Member.objects.filter(event_member_instance__team__competition__user=request.user, name=member).update(name=new_name)
                EventMemberPracticeInstance.objects.filter(practice__user=request.user, member_name=member).update(member_name=new_name)
            
            if event:  # Update event name
                new_name = remove_punctuation(name, True)
                EventMemberInstance.objects.filter(event_name=event, team__competition__user=request.user).update(event_name=new_name)
                Practice.objects.filter(user=request.user, event_name=event).update(event_name=new_name)

            return redirect("competitionListView")
    
    context = {
        "form": form,
    }
    return render(request, "data/name_change.html", context)
