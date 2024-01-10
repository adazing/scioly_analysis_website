from django.db import models
from django.forms import ModelForm
from django import forms
from .models import *
import io
import csv

def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.lower().replace("trial", "").replace("&", "and").replace("(3)","").replace("(*)","") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)","").replace("(O)","").replace("(R)","").lower() if c.isalpha() or c==" "])
    return input_string.strip().title()

class MultipleChoiceAnyField(forms.MultipleChoiceField):
    """A MultipleChoiceField with no validation."""

    def valid_value(self, *args, **kwargs):
        return True

class CompetitionSettingsForm(ModelForm):
    available_events = forms.FileField(required=True)
    # File Structure:
    # Event1,Event2 (3),Event3,Event4 <--- these are event types, all the events in each row are of the same type
    # Event5,Event6,Event7 (3), <--- (3) means that the events can hold up to 3 people (above the normal 2 ppl per event)
    # ...
    conflicting_events = forms.FileField(required=False)
    # File Structure:
    # Event1,Event2,Event4 <--- these are conflict times, all the events in each row conflict each other (are in the same timeblock)
    # Event3,Event7,
    # ...
    member_event_preferences_data = forms.FileField(required=True)
    # File Structure:
    # Member1 (S),Event1,Event4,Event2 <--- these are the ranked events people want per person
    # Member2 (O),Event3,Event6 (*),Event5 (*) <--- (*) means that it is required
    # Member3,,, <--- if no preferences, make everyone have no event rankings
    #  ^ key: (S)=senior, (O)=officer, (R)=required member
    # ...
    member_member_event_preferences_data = forms.FileField(required=False)
    # File Structure:
    # Member1,Member2,Event3 <--- this are a list of people who want to be together on a certain event
    # Member3,Member5,, <--- Null event means that any event counts
    
    # officers=MultipleChoiceAnyField(required=False)
    # required_members=MultipleChoiceAnyField(required=False)
    # seniors=MultipleChoiceAnyField(required=False)
    # required_member_event_preferences = MultipleChoiceAnyField(required=False)
    # three_member_events=MultipleChoiceAnyField(required=False)

    class Meta:
        model = GeneratedCompetitionSettings
        fields = [
            "name",
            "notes",
            "max_events_per_member",
            "min_events_per_member",
            "skill_vs_preferences",
            "min_event_experience",
            "max_num_of_build_events_per_member",
        ]
        labels= {
            "name":"Name of upcoming competition",
        }
        widgets = {
            'notes': forms.Textarea(attrs={'cols': 20, 'rows': 5}),
            'skill_vs_preferences' : forms.NumberInput(attrs={"type":"range", "min":0, "max":1, "value":0.5})
        }
    def clean_available_events(self, *args, **kwargs):
        available_events = self.cleaned_data.get("available_events")
        
        # check if ending is csv file
        if not available_events.name.endswith(".csv"):
            raise forms.ValidationError("This is not a valid csv file.")
        
        # try to read the file and validate
        try:
            available_events.seek(0)  # Reset file pointer to start
            available_events_content = io.TextIOWrapper(available_events.file, encoding='utf-8').read()
            reader = csv.reader(available_events_content.splitlines(), delimiter=',')
        except:
            raise forms.ValidationError("This is not a valid csv file.")
        list_of_events=[]
        for i, row in enumerate(reader):
            # check if row length is changes --> tampering with file?
            if i==0:
                row_length=len(row)
            elif len(row)!=row_length:
                raise forms.ValidationError("This is not a valid csv file.")
            
            # check if first cell of row has an event.
            if remove_punctuation(row[0], True)=="":
                raise forms.ValidationError("One of the rows has no event in the first cell.")

            # check for repeats
            for e in row:
                event_name = remove_punctuation(e, True)
                if event_name != "":
                    if event_name in list_of_events:
                        raise forms.ValidationError("Some of the events are repeated!")
                    list_of_events.append(event_name)


        return available_events_content
    
    def clean_conflicting_events(self, *args, **kwargs):
        conflicting_events = self.cleaned_data.get("conflicting_events")
        conflicting_events_content = None
        if conflicting_events is not None:
            
            # check if ending is csv file
            if not conflicting_events.name.endswith(".csv"):
                raise forms.ValidationError("This is not a valid csv file.")
            
            # try to read the file and validate
            try:
                conflicting_events.seek(0)  # Reset file pointer to start
                conflicting_events_content = io.TextIOWrapper(conflicting_events.file, encoding='utf-8').read()
                reader = csv.reader(conflicting_events_content.splitlines(), delimiter=',')
            except:
                raise forms.ValidationError("This is not a valid csv file.")
            
            list_of_events = []
            for i, row in enumerate(reader):
                # check if row length is changes --> tampering with file?
                if i==0:
                    row_length=len(row)
                elif len(row)!=row_length:
                    raise forms.ValidationError("This is not a valid csv file.")
                
                # check if first 2 cells of row have events.
                if remove_punctuation(row[0], True)=="":
                    raise forms.ValidationError("One of the rows has no event in the first cell.")
                # if remove_punctuation(row[1], True)=="":
                #     raise forms.ValidationError("One of the rows only has one event.")
                # check for repeats
                for e in row:
                    event_name = remove_punctuation(e, True)
                    if event_name != "":
                        if event_name in list_of_events:
                            raise forms.ValidationError("Some of the events are repeated!")
                        list_of_events.append(event_name)

        return conflicting_events_content
    
    def clean_member_event_preferences_data(self, *args, **kwargs):
        member_event_preferences = self.cleaned_data.get("member_event_preferences_data")
        
        # check if ending is csv file
        if not member_event_preferences.name.endswith(".csv"):
            raise forms.ValidationError("This is not a valid csv file.")
        
        # try to read the file and validate
        try:
            member_event_preferences.seek(0)  # Reset file pointer to start
            member_event_preferences_content = io.TextIOWrapper(member_event_preferences.file, encoding='utf-8').read()
            reader = csv.reader(member_event_preferences_content.splitlines(), delimiter=',')
            next(reader)
        except:
            raise forms.ValidationError("This is not a valid csv file.")
        
        list_of_members = []
        for i, row in enumerate(reader):
            # check if row length is changes --> tampering with file?
            if i==0:
                row_length=len(row)
            elif len(row)!=row_length:
                raise forms.ValidationError("This is not a valid csv file.")
            
            # check if member is formatted correctly
            member_name = remove_punctuation(row[0], False)
            if member_name == "":
                raise forms.ValidationError("One of the rows does not state the member in the first cell.")
            if "(O)" in row[0] and "(R)" in row[0]:
                raise forms.ValidationError("(O) is mutually exclusive with (R)")
            if member_name in list_of_members:
                raise forms.ValidationError("There are some repeating members!")
        return member_event_preferences_content

    def clean_member_member_event_preferences_data(self, *args, **kwargs):
        member_member_event_preferences = self.cleaned_data.get("member_member_event_preferences_data")
        member_member_event_preferences_content = None
        if member_member_event_preferences is not None:
            
            # check if ending is csv file
            if not member_member_event_preferences.name.endswith(".csv"):
                raise forms.ValidationError("This is not a valid csv file.")
            
            # try to read the file and validate
            try:
                member_member_event_preferences.seek(0)  # Reset file pointer to start
                member_member_event_preferences_content = io.TextIOWrapper(member_member_event_preferences.file, encoding='utf-8').read()
                reader = csv.reader(member_member_event_preferences_content.splitlines(), delimiter=',')
                next(reader)
            except:
                raise forms.ValidationError("This is not a valid csv file.")
            
            list_of_members = []
            for i, row in enumerate(reader):
                # check if row length is changes --> tampering with file?
                if i==0:
                    row_length=len(row)
                elif len(row)!=row_length:
                    raise forms.ValidationError("This is not a valid csv file.")
                
                # check if member1 is formatted correctly
                member1_name = remove_punctuation(row[0], False)
                if member1_name == "":
                    raise forms.ValidationError("One of the rows does not state the member in the first cell.")

                # check if member2 is formatted correctly
                member2_name = remove_punctuation(row[1], False)
                if member2_name == "":
                    raise forms.ValidationError("One of the rows does not state the member in the second cell.")

        return member_member_event_preferences_content


class TeamForm(ModelForm):
    required_members = forms.ModelMultipleChoiceField(
        widget = forms.CheckboxSelectMultiple,
        queryset=AvailableMember.objects.filter(status="R"), # FIX: SHOWS MEMBERS NOT SPECIFIC TO COMPETITION
        required=False
    )
    class Meta:
        model=GeneratedTeam
        fields = [
            "name",
            "notes",
            "team_size",
        ]
    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("queryset")
        super().__init__(*args, **kwargs)
        self.fields["required_members"].queryset = queryset

class DeleteConfirmationForm(forms.Form):
    confirm = forms.BooleanField()
    
