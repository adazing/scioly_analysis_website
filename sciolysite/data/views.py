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


def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.lower().replace("trial", "").replace("&", "and") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.lower() if c.isalpha() or c==" "])
    return input_string.strip().title()

@login_required
def competitionView(request, pk):
    competition=get_object_or_404(Competition, id=pk)
    if competition.user.id==request.user.id:
        print(competition)
        teams = Team.objects.filter(competition=competition)
        print(competition.name)
        context = {
            "competition" : competition,
            "team_list" : teams,
        }
        return render(request, "data/competition_view.html", context)
    raise Http404

@login_required
def competitionCreateView(request):
    form = CompetitionForm(request.POST or None)
    print(form)
    if form.is_valid():
        print("hi")
        competition = Competition.objects.create(name=form.cleaned_data.get("name"),user=request.user, date=form.cleaned_data.get("date"), number_of_teams_competed=form.cleaned_data.get("number_of_teams_competed"))
        return redirect("competitionView", pk=competition.id)
    context = {
        'form':form,
    }
    print(form.errors)
    return render(request, 'data/competition_write.html', context)

@login_required
def competitionEditView(request, pk):
    competition = get_object_or_404(Competition, id=pk)
    if competition.user.id == request.user.id:
        form = CompetitionForm(request.POST or None, instance=competition)
        if form.is_valid():
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
                next(reader)
                team = Team.objects.create(name=team_name, competition=competition)
                for row in reader: # VERY GOOD FOR ARMITA
                    event_name=row[0]
                    event_name = remove_punctuation(event_name, True)
                    score = int(row[4])
                    if event_name!="":
                        event_member_instance = EventMemberInstance.objects.create(event_name=event_name, team=team, score=score)
                        for m in range(1,4):
                            member_name = remove_punctuation(row[m], False)
                            if member_name!="":
                                member = Member.objects.create(name=member_name, event_member_instance=event_member_instance)
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
            score_color=max(0,(e_m_i.score/team.competition.number_of_teams_competed)*100)
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

        context = {
            "team" : team,
            "results" : results,
            "results2" : results2
        }
        return render(request, "data/team_view.html", context)
    raise Http404

@login_required
def competitionListView(request):
    competitions = Competition.objects.filter(user=request.user.id)
    context = {
        "competition_list":competitions,
    }
    return render(request, "data/competition_list.html", context)

@login_required
def skillView(request):
    # list of members that have been in all the competition so far
    member_list=Member.objects.filter(event_member_instance__team__competition__user=request.user)
    
    # dictionary that maps member names to a dictionary that maps event names to skill levels
    members_to_skill_level=dict()
    
    # set of all the events that have occured across all the competitions
    all_events=set()
    
    # dictionary that maps member names to a dictionary that maps event names to # of times the member did that event
    members_to_experience=dict()
    
    # dictionary that maps member names to a dictionary that maps event names to html popup when clicking on the cell
    members_to_data = dict()
    
    average_scores_of_competition_cache = {}
    for member in member_list:
        all_events.add(member.event_member_instance.event_name)
        # did not quit/get disqualified
        if member.event_member_instance.score<=member.event_member_instance.team.competition.number_of_teams_competed:
            competition=member.event_member_instance.team.competition
            if competition.id in average_scores_of_competition_cache:
                average_score_of_team = average_scores_of_competition_cache[competition.id]
            else:
                school_scores_of_competition=[]
                for team in Team.objects.filter(competition=member.event_member_instance.team.competition):
                    school_scores_of_competition+=[x.score for x in EventMemberInstance.objects.filter(team=team) if x.score<=x.team.competition.number_of_teams_competed]
                average_score_of_team=sum(school_scores_of_competition)/len(school_scores_of_competition)
                average_scores_of_competition_cache[competition.id] = average_score_of_team
            score=average_score_of_team/member.event_member_instance.team.competition.number_of_teams_competed-member.event_member_instance.score/member.event_member_instance.team.competition.number_of_teams_competed
            if member.name in members_to_skill_level:
                if member.event_member_instance.event_name in members_to_skill_level[member.name]:
                    members_to_skill_level[member.name][member.event_member_instance.event_name]+=score
                    members_to_data[member.name][member.event_member_instance.event_name]+="<li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
                    members_to_experience[member.name][member.event_member_instance.event_name]+=1
                else:
                    members_to_skill_level[member.name][member.event_member_instance.event_name]=score
                    members_to_data[member.name][member.event_member_instance.event_name]="<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
                    members_to_experience[member.name][member.event_member_instance.event_name]=1
            else:
                members_to_skill_level[member.name]={}
                members_to_skill_level[member.name][member.event_member_instance.event_name]=score
                members_to_data[member.name]={}
                members_to_data[member.name][member.event_member_instance.event_name]="<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
                members_to_experience[member.name]={}
                members_to_experience[member.name][member.event_member_instance.event_name]=1
    
    min_score = min([min(members_to_skill_level[m].values()) for m in members_to_skill_level])
    max_score = max([max(members_to_skill_level[m].values()) for m in members_to_skill_level])
    all_events = sorted(list(all_events))
    table_columns = ["Name"]+all_events
    max_xp = max([max(members_to_experience[m].values()) for m in members_to_experience])
    
    table_info_data = [["".join([members_to_data[m][e]+"</ul>" for e in members_to_skill_level[m]])]+[members_to_data[m][e]+"</ul>" if e in members_to_skill_level[m] else "<p>No Data</p>" for e in all_events] for m in members_to_skill_level]
    print(members_to_skill_level)
    table_data = [[m]+[(members_to_skill_level[m][e]-min_score)*100/(max_score-min_score) if e in members_to_skill_level[m] else 0 for e in all_events] for m in members_to_skill_level]
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
    }
    return render(request, "data/skill_view.html", context)