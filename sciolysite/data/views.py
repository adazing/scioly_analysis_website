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
    
    # event_to_members = {}
    
    # event_to_emis = {}
    # for emi in EventMemberInstance.objects.all():
    #     competition=emi.team.competition
    #     if emi.score<=competition.number_of_teams_competed:
    #         if competition.id in average_scores_of_competition_cache:
    #             average_score_of_team = average_scores_of_competition_cache[competition.id]
    #         else:
    #             school_scores_of_competition=[]
    #             for team in Team.objects.filter(competition=competition):
    #                 school_scores_of_competition+=[x.score for x in EventMemberInstance.objects.filter(team=team) if x.score<=x.team.competition.number_of_teams_competed]
    #             average_score_of_team=sum(school_scores_of_competition)/len(school_scores_of_competition)
    #             average_scores_of_competition_cache[competition.id] = average_score_of_team
    #         members_in_emi = [m.name for m in Member.objects.filter(event_member_instance=emi)]
    #         if emi.event_name in event_to_emis:
    #             for m in members_in_emi:
    #                 if m not in event_to_members[emi.event_name]:
    #                     event_to_members[emi.event_name][m] = 0
    #             event_to_emis[emi.event_name].append([(average_scores_of_competition_cache[competition.id]-emi.score)/competition.number_of_teams_competed]+ members_in_emi)
    #         else:
    #             event_to_emis[emi.event_name]=[[(average_scores_of_competition_cache[competition.id]-emi.score)/competition.number_of_teams_competed]+ members_in_emi]
    #             event_to_members[emi.event_name] = dict()
    #             for m in members_in_emi:
    #                 if m not in event_to_members[emi.event_name]:
    #                     event_to_members[emi.event_name][m] = 0
    # # print(event_to_members)
    # # print(event_to_emis)
    
    # for event in event_to_emis:
    #     matrix = []
    #     result = []
    #     members_in_event = sorted(list(event_to_members[event].keys()))
    #     # print(members_in_event)
    #     for emi in event_to_emis[event]:
    #         matrix.append([0 for i in members_in_event])
    #         for m in emi[1:]:
    #             matrix[-1][members_in_event.index(m)]=1
    #         result.append(emi[0])
    #     matrix = np.array(matrix)
    #     result = np.array(result)
    #     result = np.dot(matrix.T, result)
    #     matrix = np.dot(matrix.T,matrix)
    #     # print(result)
    #     # print(result.shape)
    #     # print(matrix)
    #     # print(matrix.shape)
    #     solution = list(np.linalg.lstsq(matrix, result, rcond=None)[0])
    #     for s in range(len(solution)):
    #         event_to_members[event][members_in_event[s]]+=solution[s]
    #     # print(event_to_members[event][members_in_event[s]])
    #     # print(matrix)
    #     # print(result)
        
    # print(event_to_members)
    
    
            
    
    # idea: DID NOT WORK
    # iterate over all EventMemberInstance instances
    #   add a
    # find member-member pair + score that they got in comp
    # order all the people that participated in the event so far alphabetically
    # make matrix
    # find solution
    # convert back to regular person-dictionary scores
    # 
    
    # idea: Kevin's idea
    # members_to_skill_level = dict()
    # iterate over all competitions, ordered from first to last by date
    #   add 
    
    # for member in member_list:
    #     all_events.add(member.event_member_instance.event_name)
    #     # did not quit/get disqualified
    #     if member.event_member_instance.event_name in event_to_members:
    #         if member.name in members_to_skill_level:
    #             if member.event_member_instance.event_name in members_to_skill_level[member.name]:
    #                 members_to_skill_level[member.name][member.event_member_instance.event_name]+=event_to_members[member.event_member_instance.event_name][member.name]
    #                 members_to_data[member.name][member.event_member_instance.event_name]+="<li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
    #                 members_to_experience[member.name][member.event_member_instance.event_name]+=1
    #             else:
    #                 members_to_skill_level[member.name][member.event_member_instance.event_name]=event_to_members[member.event_member_instance.event_name][member.name]
    #                 members_to_data[member.name][member.event_member_instance.event_name]="<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
    #                 members_to_experience[member.name][member.event_member_instance.event_name]=1
    #         else:
    #             members_to_skill_level[member.name]={}
    #             members_to_skill_level[member.name][member.event_member_instance.event_name]=event_to_members[member.event_member_instance.event_name][member.name]
    #             members_to_data[member.name]={}
    #             members_to_data[member.name][member.event_member_instance.event_name]="<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
    #             members_to_experience[member.name]={}
    #             members_to_experience[member.name][member.event_member_instance.event_name]=1

    '''
    idea:
    members_to_skill_level = dict()
    for member in competition:
        
        
    '''
    members_to_skill_level = dict()
    members_to_experience = dict()
    members_to_data = dict()
    all_events=set()
    for c in Competition.objects.filter(user=request.user).order_by('date'):
        emis_list = EventMemberInstance.objects.filter(team__competition=c)
        school_scores_of_competition = [x.score for x in EventMemberInstance.objects.filter(team__competition=c) if x.score<=x.team.competition.number_of_teams_competed]
        average_score_of_team=sum(school_scores_of_competition)/len(school_scores_of_competition)
        for emi in emis_list:
            all_events.add(emi.event_name)
            if emi.score <= c.number_of_teams_competed:
                score = (average_score_of_team - emi.score) / c.number_of_teams_competed
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
                total_experience = sum([members_to_experience[member][event] for member in members])
                # total_skill = sum([members_to_skill_level[member][event] for member in members])
                for m in members:
                    # if total_skill != 0:
                        # members_to_skill_level[m][event] += membrs_to_skill_level[m][event]/total_skill*score
                    # else:
                    members_to_skill_level[m][event] += members_to_experience[m][event]/total_experience * score
                    # members_to_skill_level[m][event] += members_to_experience[m][event]/total_experience * score
    # print(members_to_skill_level)

    # # print(members_to_skill_level)
    # # print(members_to_data)
    # print(members_to_data["Emma Zheng"])

    # print("-"*100)
    # members_to_skill_level = dict()
    # members_to_experience = dict()
    # members_to_data = dict()
    # all_events=set()

    # for member in member_list:
    #     all_events.add(member.event_member_instance.event_name)
    #     # did not quit/get disqualified
    #     if member.event_member_instance.score<=member.event_member_instance.team.competition.number_of_teams_competed:
    #         competition=member.event_member_instance.team.competition
    #         if competition.id in average_scores_of_competition_cache:
    #             average_score_of_team = average_scores_of_competition_cache[competition.id]
    #         else:
    #             school_scores_of_competition=[]
    #             for team in Team.objects.filter(competition=member.event_member_instance.team.competition):
    #                 school_scores_of_competition+=[x.score for x in EventMemberInstance.objects.filter(team=team) if x.score<=x.team.competition.number_of_teams_competed]
    #             average_score_of_team=sum(school_scores_of_competition)/len(school_scores_of_competition)
    #             average_scores_of_competition_cache[competition.id] = average_score_of_team
    #         score=average_score_of_team/member.event_member_instance.team.competition.number_of_teams_competed-member.event_member_instance.score/member.event_member_instance.team.competition.number_of_teams_competed
    #         if member.name in members_to_skill_level:
    #             if member.event_member_instance.event_name in members_to_skill_level[member.name]:
    #                 members_to_skill_level[member.name][member.event_member_instance.event_name]+=score
    #                 members_to_data[member.name][member.event_member_instance.event_name]+="<li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
    #                 members_to_experience[member.name][member.event_member_instance.event_name]+=1
    #             else:
    #                 members_to_skill_level[member.name][member.event_member_instance.event_name]=score
    #                 members_to_data[member.name][member.event_member_instance.event_name]="<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
    #                 members_to_experience[member.name][member.event_member_instance.event_name]=1
    #         else:
    #             members_to_skill_level[member.name]={}
    #             members_to_skill_level[member.name][member.event_member_instance.event_name]=score
    #             members_to_data[member.name]={}
    #             members_to_data[member.name][member.event_member_instance.event_name]="<ul style='padding:0;  margin-top:10px; margin-bottom:0;'><li>"+member.event_member_instance.team.competition.name+" "+member.event_member_instance.team.name+": ranked "+str(member.event_member_instance.score)+"/"+str(member.event_member_instance.team.competition.number_of_teams_competed)+" in "+member.event_member_instance.event_name+"</li>"
    #             members_to_experience[member.name]={}
    #             members_to_experience[member.name][member.event_member_instance.event_name]=1
    # print(members_to_data["Emma Zheng"])
    # print(members_to_data)
    
    # print(members_to_experience)
    
    min_score = min([min(members_to_skill_level[m].values()) for m in members_to_skill_level])
    max_score = max([max(members_to_skill_level[m].values()) for m in members_to_skill_level])
    
    for m in members_to_experience:
        for e in members_to_experience[m]:
            if members_to_experience[m][e] == 1:
                members_to_skill_level[m][e] = min_score

    all_events = sorted(list(all_events))
    table_columns = ["Name"]+all_events
    max_xp = max([max(members_to_experience[m].values()) for m in members_to_experience])
    
    table_info_data = [["".join([members_to_data[m][e]+"</ul>" for e in members_to_skill_level[m]])]+[members_to_data[m][e]+"</ul>" if e in members_to_skill_level[m] else "<p>No Data</p>" for e in all_events] for m in members_to_skill_level]
    # print(members_to_skill_level)
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