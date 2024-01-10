from django.shortcuts import render
from .forms import *
import csv

# Create your views here.

def TeamFormViewConflictData(request):
    form = Team_Form(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            reader = csv.reader(form.cleaned_data.get("events").splitlines(), delimiter=',')
            reader = csv.reader(form.cleaned_data.get("conflicting events").splitlines(), delimiter=',')
            
            for row in reader:
                

            for rows in reader_con:
                event_name=row[0]
                    event_name = remove_punctuation(event_name, True)
                    score = int(row[4])
                    if event_name!="":
                        
                        for m in range(1,4):
                            member_name = remove_punctuation(row[m], False)
                            if member_name!="":
                                
                    else: # reached end
                        break




