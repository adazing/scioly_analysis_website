from django.shortcuts import render
from .forms import *
import csv

# Create your views here.
def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.lower().replace("trial", "").replace("&", "and").replace("(3)","").replace("(*)","") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)","").replace("(O)","").replace("(R)","").lower() if c.isalpha() or c==" "])
    return input_string.strip().title()


def ConflictCheckingView(request):
    form = ConflictCheckingForm(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            team_data_reader = csv.reader(form.cleaned_data.get("team_data").splitlines(), delimiter=',')
            conflicting_events_reader = csv.reader(form.cleaned_data.get("conflicting_events").splitlines(), delimiter=',')
            
            conflicting_events = []
            for row in conflicting_events_reader:
                conflicting_events.append([remove_punctuation(e, True) for e in row])
                

            for row in team_data_reader:
                event_name=remove_punctuation(row[0], True)
                member1 = remove_punctuation(row[1], True)




