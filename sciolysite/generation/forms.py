from django.db import models
from django.forms import ModelForm
from django import forms
from .models import *
import io
from .models import *
import csv
# from django.core.exceptions import ValidationError
# from django.shortcuts import get_object_or_404, redirect


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
            # check if row length changes --> tampering with file?
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
                # check if row length changes --> tampering with file?
                if i==0:
                    row_length=len(row)
                elif len(row)!=row_length:
                    raise forms.ValidationError("This is not a valid csv file.")
                
                # check if first cell of row have event.
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
            # next(reader)
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
            # if "(O)" in row[0] and "(R)" in row[0]:
            #     raise forms.ValidationError("(O) is mutually exclusive with (R)")
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
                # next(reader)
            except:
                raise forms.ValidationError("This is not a valid csv file.")
            
            # list_of_members = []
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
    # required_members = forms.ModelMultipleChoiceField(
    #     # widget = forms.CheckboxSelectMultiple,
    #     queryset = AvailableMember.objects.all(),
    #     # queryset=AvailableMember.objects.filter(status="R"), # FIX: SHOWS MEMBERS NOT SPECIFIC TO COMPETITION
    #     required=False
    # )
    class Meta:
        model=GeneratedTeam
        fields = [
            "name",
            "notes",
            "team_size",
        ]
    def __init__(self, *args, **kwargs):
        # queryset = kwargs.pop("queryset")
        super().__init__(*args, **kwargs)
        # self.fields["required_members"].queryset = queryset
    def clean_team_size(self):
        team_size = self.cleaned_data["team_size"]
        if team_size < 1:
            raise forms.ValidationError("Team size is too small (must be at least 1).")
        elif team_size > 15:
            raise forms.ValidationError("Team size is too large (must be at most 15).")
    
class RequirementsForm(ModelForm):
    class Meta:
        model=RequiredMemberToTeam
        fields = [
            "member",
            "event",
        ]
    def __init__(self, *args, **kwargs):
        member_queryset = kwargs.pop("member_queryset")
        event_queryset = kwargs.pop("event_queryset")
        generated_team = kwargs.pop("generated_team")
        requirements = kwargs.pop("requirements")
        # events_with_3_members = kwargs.pop("events_with_3_members")
        members_required_in_other_teams = kwargs.pop("members_required_in_other_teams")
        # event_conflicts = kwargs.pop("event_conflicts")
        self.generated_team = generated_team
        self.requirements = requirements
        # self.events_with_3_members = events_with_3_members
        self.members_required_in_other_teams = members_required_in_other_teams
        # self.event_conflicts = event_conflicts
        self.fields["member"].queryset = member_queryset
        self.fields["event"].queryset = event_queryset
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        member_id = cleaned_data['member']
        event_id = cleaned_data['event']
        required_members = []
        events_to_members = {}
        for r in self.requirements:
            if r.member not in required_members:
                required_members.append(r.member)
            if r.event:
                if r.event not in events_to_members:
                    events_to_members[r.event] = [r.member]
                elif r.event in events_to_members:
                    events_to_members[r.event].append(r.member)
        if event_id:
            event = AvailableEvent.objects.get(id = event_id)
        else:
            event = None
        member = AvailableMember.objects.get(id = member_id)

        # new member would cause the team to go over the size limit
        if len(required_members) >= self.generated_team.generated_competition_settings.team_size:
            raise forms.ValidationError("You have required too many members to be on the same team.")

        if member.is_senior:
            seniors = [m for m in required_members if m.is_senior]
            # check if too many seniors have been assigned
            if len(seniors) >= 7:
                raise forms.ValidationError("Too many assigned seniors.")

        events_done_by_member = [e for e in events_to_members if member in events_to_members[e]]
        # member is already required in a different team
        if member in self.members_required_in_other_teams:
            raise forms.ValidationError(member.name + " is already required on a different team")
        # too many events required by member
        if len(events_done_by_member) >= self.generated_team.generated_competition_settings.max_events_per_member:
            raise forms.ValidationError("Too many events required for "+member.name)
        # member is already required on the event
        if event in events_done_by_member:
            raise forms.ValidationError("This requirement already exists")
        
        
        if event != None:
            # there is already enough members in the event
            if len(events_to_members[event])>=2+(event.needs_3_members):
                raise forms.ValidationError("Too many members are required for the event "+event.name)
        
            # member has already reached max build events
            if event.is_build_event:
                build_events_that_member_has = [e for e in events_done_by_member if e.is_build_event]
                if len(build_events_that_member_has) + 1>self.generated_team.generated_competition_settings.max_num_of_build_events_per_member:
                    raise forms.ValidationError("Too many build events are required for "+member.name)
        
        # check if assigned to conflicting events 
        conflicts = []
        for e in events_done_by_member+[event]:
            if e.conflict in conflicts:
                raise forms.ValidationError(member.name+" cannot be placed in two events that have conflicting time slots.")
            conflicts.append(e.conflict)
        return cleaned_data
        # 
        # cleaned_data = super().clean()
        # member_id = self.cleaned_data['member']
        # team_id = self.cleaned_data['team']
        # event_id = self.cleaned_data['event']
        
        # team = GeneratedTeam.objects.get(id=team_id)
        # requirements = RequiredMemberToTeam.objects.filter(team=team)
        # members_used = []
        # event_count = dict()
        # for r in requirements:
        #     if len(members_used)>team.team_size:
        #         # TODO: FIIIXXXX TEAM MIGHT NOT EVEN EXIST YETT AHHHH MAYBE SEPARATE PAGE TO ADD REQUIREMENTS???
        #         raise forms.ValidationError("The number of required members is greater than the max team size.")
        #     if r.member not in members_used:
        #         members_used.append(r.member)
            
        

        # if data is not None and data != '':
        #     try:
        #         data = int(data)
        #     except ValueError:
        #         raise forms.ValidationError("Invalid ID format. Must be an integer.")
        # return data

'''
        
        // already enough events for the member
        if (events_done_by_member.length >= max_events_per_member) {
            {% comment %} console.log(1); {% endcomment %}
            return false;
        }
        // member is already in the event
        else if (team[event].includes(member)) {
            {% comment %} console.log(2); {% endcomment %}
            return false;
        }
        // there is already enough members in the event
        else if (team[event].length >= 2 + (events_with_3_members.includes(event) ? 1 : 0)) {
            {% comment %} console.log(3); {% endcomment %}
            return false;
        }
        // member has already reached max build events
        else if (events_done_by_member.filter(function(e) {
            return build_events.includes(e);
        }).length >= max_num_of_build_events_per_member) {
            {% comment %} console.log(4); {% endcomment %}
            return false;
        }
        // new member would cause the team to go over the size limit
        else if (members_on_team.size + 1 > team_size && !members_on_team.has(member)) {
            {% comment %} console.log(5); {% endcomment %}
            return false;
        }
        
        // adding member to event would cause conflicts
        events_done_by_member.push(event);
        var conflicts = Array(conflicting_events.length).fill(0);
        for (e of events_done_by_member){
            //console.log(e);
            for (index in conflicting_events){
                if (conflicting_events[index].includes(e)){
                    conflicts[index] += 1;
                }
                if (conflicts[index]>1){
                    {% comment %} console.log(6); {% endcomment %}
                    return false;
                }
            }
    // senior restrictions

'''

class DeleteConfirmationForm(forms.Form):
    confirm = forms.BooleanField()
    
