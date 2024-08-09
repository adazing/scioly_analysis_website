from django.db import models
from django.forms import ModelForm
from django import forms
from .models import *
import csv
import io

def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.lower().replace("&", "and") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.lower() if c.isalpha() or c==" "])
    return input_string.strip().title()


class CompetitionForm(ModelForm):
    class Meta:
        model = Competition
        fields = [
            "name",
            "date",
            "number_of_teams_competed",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type":"date"}),
            "number_of_teams_competed" : forms.NumberInput(attrs={'min':0,'type': 'number'}),
        }
        labels = {
            "name" : "Name of competition",
            "date" : "Date of competition",
            "number_of_teams_competed" : "Total number of teams that participated in the Competition",
        }
    def clean_number_of_teams_competed(self):
        number_of_teams_competed = self.cleaned_data.get("number_of_teams_competed")
        if number_of_teams_competed<=0:
            raise forms.ValidationError("The number of teams that competed is too low.")
        return number_of_teams_competed

class TeamForm(ModelForm):
    # SHOULD VALIDATE AND PUT ATTRS THING ON OTHER STUFF ARMITA PLS REMIND ME
    score_data = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}), label="Score CSV data")
    class Meta:
        model = Team
        fields = [
            "name"
        ]
        labels = {
            "name": "Name of Team"
        }
    def clean_score_data(self, *args, **kwargs):
        score_data = self.cleaned_data.get("score_data")
        
        if score_data.size > 1 * 1024 * 1024:  # 1MB limit
            raise forms.ValidationError("File size must be under 1MB.")
        
        # check if ending is csv file
        if not score_data.name.endswith(".csv"):
            raise forms.ValidationError("This is not a valid csv file.")
        
        # try to read the file and validate
        try:
            score_data.seek(0)  # Reset file pointer to start
            score_data_content = io.TextIOWrapper(score_data.file, encoding='utf-8').read()
            reader = csv.reader(score_data_content.splitlines(), delimiter=',')
            # next(reader)  # Skip header
        except:
            raise forms.ValidationError("This is not a valid csv file.")
        row_num = 0
        done_events = []
        for i, row in enumerate(reader):
            # see if row length is changes --> tampering with file?
            if i==0:
                row_length=len(row)
            elif len(row)!=row_length:
                raise forms.ValidationError("This is not a valid csv file.")
            
            if row_length != 5:
                raise forms.ValidationError("This is not the correct format. The length of each row should be 5 (event, member1, member2, member3, score).")
            
            # see if score is an int
            try:
                score = int(row[4].strip())
            except:
                raise forms.ValidationError("Some of the scores are non-integer values.")
            
            # if event_name is blank, means reached end of file
            event_name=row[0]
            event_name = remove_punctuation(event_name, True)
            if event_name!="":
                # event is repeated?
                if event_name in done_events:
                    raise forms.ValidationError("There are some event repeats.")
                
                # first member exists
                if remove_punctuation(row[1], False) == "":
                    raise forms.ValidationError("One of the events has no people on it.")
                    
                done_events.append(event_name)
                row_num += 1
            else: # reached end
                break
        if row_num <= 0:
            raise forms.ValidationError("Not enough valid rows.")
        elif row_num >= 50:
            raise forms.ValidationError("Cannot have more than 50 rows.")
        return score_data_content

class DeleteConfirmationForm(forms.Form):
    confirm = forms.BooleanField()
    
    
class NameChangeForm(forms.Form):
    member = forms.ChoiceField(choices = (), required=False, label="Original Member Name")
    event = forms.ChoiceField(choices = (), required=False, label="Original Event Name")
    name = forms.CharField(max_length = 100, required=True, label="New Name")
    def __init__(self, *args, **kwargs):
        member_queryset = kwargs.pop("member_queryset")
        event_queryset = kwargs.pop("event_queryset")
        super().__init__(*args, **kwargs)
        self.fields["member"].choices = member_queryset
        self.fields["event"].choices = event_queryset
    def clean(self):
        cleaned_data = self.cleaned_data
        event = self.cleaned_data.get("event")
        event = event if event else None
        member = self.cleaned_data.get("member")
        member = member if member else None
        name = self.cleaned_data.get("name")
        if event == None and member == None:
            raise forms.ValidationError("You must specify what you are replacing in the data.")
        elif event != None and member != None:
            raise forms.ValidationError("Error submitting form.")
        elif member == None:
            if remove_punctuation(name, True) == "":
                raise forms.ValidationError("Replacement name is not valid.")
        elif event == None:
            if remove_punctuation(name, False) == "":
                raise forms.ValidationError("Replacement name is not valid.")
        return cleaned_data
