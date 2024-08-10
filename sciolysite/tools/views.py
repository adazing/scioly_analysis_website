from django.shortcuts import render
from .forms import *
import csv

# Create your views here.
def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.replace("(B)", "").replace("(3)", "").lower().replace("&", "and") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)", "").lower() if c.isalpha() or c==" "])
    return input_string.strip().title()


def ConflictCheckingView(request):
    form = ConflictCheckingForm(request.POST or None, request.FILES or None)
    
    if request.method == "POST":
        if form.is_valid():
            team_data_reader = csv.reader(form.cleaned_data.get("team_data").splitlines(), delimiter=',')
            conflicting_events_reader = csv.reader(form.cleaned_data.get("conflicting_events").splitlines(), delimiter=',')
            
            conflicting_events = []
            for row in conflicting_events_reader:
                if remove_punctuation(row[0], True) != "":
                    conflicting_events.append([remove_punctuation(e, True) for e in row])
                    
                        
            team = {}
            members_to_events = {}
            for row in team_data_reader:
                event_name=remove_punctuation(row[0], True)
                if event_name !="":
                    for m in range(1, min(len(row), 4)):
                        member_name = remove_punctuation(row[m], False)
                        if member_name != "":
                            if member_name in members_to_events:
                                members_to_events[member_name].append(event_name)
                            else:
                                members_to_events[member_name] = [event_name]
                            if event_name in team:
                                team[event_name].append(member_name)
                            else:
                                team[event_name] = [member_name]
                else:
                    break

            table_team = []
            team_keys = list(team.keys())
            for e in team_keys:
                table_team.append([e])
                table_team[-1] += [{"member":m,"color":"#FFFFFF"} for m in team[e]] + [{"member":"", "color":"#FFFFFF"} for x in range(3 - len(team[e]))]
            print(table_team)
            
            found_conflicts = []
            for m in members_to_events:
                conflicts = [[] for i in conflicting_events]
                for e in members_to_events[m]:
                    for c in range(len(conflicting_events)):
                        if e in conflicting_events[c]:
                            conflicts[c].append(e)
                for conflict in conflicts:
                    # table_team.index(team)
                    # table_team[conflict] 
                    # conflict found!
                    if len(conflict) > 1:
                        for e in conflict:
                            row_idx = team_keys.index(e)
                            # row = table_team[team_keys.index(e)]
                            for m_idx in range(1, 4):
                                m_name = table_team[row_idx][m_idx]["member"]
                                if m_name == m:
                                    table_team[row_idx][m_idx]["color"] = "#FF6961"
                        english_conflict = ", ".join(conflict[:-1])
                        found_conflicts.append(f"{m} is in {english_conflict} and {conflict[-1]}")
            
            # MAYBE DISPLAY SUGGESTIONS?
            
            context = {
                "team" : table_team,
                "found_conflicts" : found_conflicts,
                "form" : form,
                "conflicting_events" : conflicting_events,
            }
            return render(request, "tools/conflict_checking.html", context)
    context = {
        "form" : form,
    }
    return render(request, 'tools/conflict_checking_form.html', context)


        # for i, row in enumerate(reader):
        #     # see if row length is changes --> tampering with file?
        #     if i==0:
        #         row_length=len(row)
        #     elif len(row)!=row_length:
        #         raise forms.ValidationError("This is not a valid csv file.")

        #     # if event_name is blank, means reached end of file
        #     event_name=row[0]
        #     event_name = remove_punctuation(event_name, True)
        #     if event_name!="":
        #         if event_name in done_events:
        #             raise forms.ValidationError("There are some event repeats.")
        #         is_at_least_one_member_on_event = False
        #         for m in range(1,min(row_length, 4)):
        #             member_name = remove_punctuation(row[m], False)
        #             if member_name!="":
        #                 is_at_least_one_member_on_event =True
        #         if not is_at_least_one_member_on_event:
        #             raise forms.ValidationError("One of the events has no people on it.")
        #         done_events.append(event_name)
        #     else: # reached end
        #         break
            # num_rows += 1
