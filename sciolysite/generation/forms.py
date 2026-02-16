from django.db import models
from django.forms import ModelForm
from django import forms
from .models import *
import io
from .models import *
import csv
# from django.core.exceptions import ValidationError
# from django.shortcuts import get_object_or_404, redirect


def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces, then title-case
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.replace("(B)", "").replace("(3)", "").replace("&", "and") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)", "") if c.isalpha() or c==" "])
    return input_string.strip().title()

def remove_team_name_punctuation(input_string):
    input_string = str(input_string)
    input_string = "".join([c for c in input_string if c.isalpha() or c==" "])
    return input_string

class MultipleChoiceAnyField(forms.MultipleChoiceField):
    """A MultipleChoiceField with no validation."""

    def valid_value(self, *args, **kwargs):
        return True

class CompetitionSettingsForm(ModelForm):
    available_events = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}), required=False)
    conflicting_events = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}), required=False)
    member_event_preferences_data = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}), required=False)
    member_member_event_preferences_data = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}), required=False)
    
    
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
            "max_num_of_build_events_per_member",
            "use_ranking",
            "partner_preference_weight",
            "randomization",
        ]
        labels = {
            "name": "Name of upcoming competition",
            "skill_vs_preferences": "Event Preference Weight",
            "use_ranking": "Use Ranked Event Preferences",
            "partner_preference_weight": "Partner Preference Weight",
            "randomization": "Randomization",
        }
        help_texts = {
            "max_events_per_member": "The most events any single member can be assigned to.",
            "min_events_per_member": "The fewest events any single member can be assigned to. Must be at least 1.",
            "skill_vs_preferences": "How much weight to give event preferences when generating teams. 0 = ignore preferences (skill only), 1 = full weight on preferences.",
            "max_num_of_build_events_per_member": "The most build events any single member can be assigned to.",
            "use_ranking": "When enabled, higher-ranked preferences count more than lower-ranked ones. When disabled, all listed preferences are weighted equally.",
            "partner_preference_weight": "How much weight to give partner preferences (members wanting to be on the same event together). 0 = ignore, 1 = full weight.",
            "randomization": "Adds random noise to each member-event assignment score. 0 = no randomness (deterministic), 1 = maximum randomness. Uses a seeded RNG so regenerating produces the same result.",
        }
        widgets = {
            'notes': forms.Textarea(attrs={'cols': 20, 'rows': 5}),
            'skill_vs_preferences': forms.NumberInput(attrs={"type": "range", "min": 0, "max": 1, "value": 0.5}),
            'partner_preference_weight': forms.NumberInput(attrs={"type": "range", "min": 0, "max": 1, "step": 0.05, "value": 0.05}),
            'randomization': forms.NumberInput(attrs={"type": "range", "min": 0, "max": 1, "step": 0.05, "value": 0}),
        }

    def clean_skill_vs_preferences(self):
        skill_vs_preferences = self.cleaned_data.get("skill_vs_preferences")
        if skill_vs_preferences > 1 or skill_vs_preferences < 0:
            raise forms.ValidationError("Skill vs preferences should be between 0 and 1")
        return skill_vs_preferences
    def clean_partner_preference_weight(self):
        partner_preference_weight = self.cleaned_data.get("partner_preference_weight")
        if partner_preference_weight < 0 or partner_preference_weight > 1:
            raise forms.ValidationError("Partner preference weight should be between 0 and 1")
        return partner_preference_weight
    def clean_randomization(self):
        randomization = self.cleaned_data.get("randomization")
        if randomization < 0 or randomization > 1:
            raise forms.ValidationError("Randomization should be between 0 and 1")
        return randomization
    def clean_min_events_per_member(self):
        min_events_per_member = self.cleaned_data.get("min_events_per_member")
        if min_events_per_member < 1:
            raise forms.ValidationError("The minimum events per member cannot be smaller than 1.")
        return min_events_per_member

    
    def clean_available_events(self, *args, **kwargs):
        available_events = self.cleaned_data.get("available_events")
        if available_events is None:
            return None

        if available_events.size > 1 * 1024 * 1024:  # 1MB limit
            raise forms.ValidationError("File size must be under 1MB.")

        if not available_events.name.endswith(".csv"):
            raise forms.ValidationError("This is not a valid csv file.")

        try:
            available_events.seek(0)
            available_events_content = io.TextIOWrapper(available_events.file, encoding='utf-8').read()
            reader = csv.reader(available_events_content.splitlines(), delimiter=',')
        except:
            raise forms.ValidationError("This is not a valid csv file.")

        list_of_events = []
        for i, row in enumerate(reader):
            # skip empty rows
            if not row or remove_punctuation(row[0], True) == "":
                continue
            for e in row:
                event_name = remove_punctuation(e, True)
                if event_name != "":
                    if event_name in list_of_events:
                        raise forms.ValidationError(f"Duplicate event name found: \"{event_name}\".")
                    list_of_events.append(event_name)
                else:
                    break

        return available_events_content
    
    def clean_conflicting_events(self, *args, **kwargs):
        conflicting_events = self.cleaned_data.get("conflicting_events")
        conflicting_events_content = None
        if conflicting_events is not None:

            if conflicting_events.size > 1 * 1024 * 1024:  # 1MB limit
                raise forms.ValidationError("File size must be under 1MB.")

            if not conflicting_events.name.endswith(".csv"):
                raise forms.ValidationError("This is not a valid csv file.")

            try:
                conflicting_events.seek(0)
                conflicting_events_content = io.TextIOWrapper(conflicting_events.file, encoding='utf-8').read()
                reader = csv.reader(conflicting_events_content.splitlines(), delimiter=',')
            except:
                raise forms.ValidationError("This is not a valid csv file.")

            list_of_events = []
            for i, row in enumerate(reader):
                # skip empty rows
                if not row or remove_punctuation(row[0], True) == "":
                    continue
                for e in row:
                    event_name = remove_punctuation(e, True)
                    if event_name != "":
                        if event_name in list_of_events:
                            raise forms.ValidationError(f"Duplicate event name found in conflicts: \"{event_name}\".")
                        list_of_events.append(event_name)
                    else:
                        break

        return conflicting_events_content
    
    def clean_member_event_preferences_data(self, *args, **kwargs):
        member_event_preferences = self.cleaned_data.get("member_event_preferences_data")
        if member_event_preferences is None:
            return None

        if member_event_preferences.size > 1 * 1024 * 1024:  # 1MB limit
            raise forms.ValidationError("File size must be under 1MB.")

        if not member_event_preferences.name.endswith(".csv"):
            raise forms.ValidationError("This is not a valid csv file.")

        try:
            member_event_preferences.seek(0)
            member_event_preferences_content = io.TextIOWrapper(member_event_preferences.file, encoding='utf-8').read()
            reader = csv.reader(member_event_preferences_content.splitlines(), delimiter=',')
        except:
            raise forms.ValidationError("This is not a valid csv file.")

        list_of_members = []
        for i, row in enumerate(reader):
            if not row:
                continue
            member_name = remove_punctuation(row[0], False)
            # skip empty rows
            if member_name == "":
                continue
            if member_name in list_of_members:
                raise forms.ValidationError(f"Duplicate member name found: \"{member_name}\".")
            list_of_members.append(member_name)

        return member_event_preferences_content

    def clean_member_member_event_preferences_data(self, *args, **kwargs):
        member_member_event_preferences = self.cleaned_data.get("member_member_event_preferences_data")
        member_member_event_preferences_content = None
        if member_member_event_preferences is not None:

            if member_member_event_preferences.size > 1 * 1024 * 1024:  # 1MB limit
                raise forms.ValidationError("File size must be under 1MB.")

            if not member_member_event_preferences.name.endswith(".csv"):
                raise forms.ValidationError("This is not a valid csv file.")

            try:
                member_member_event_preferences.seek(0)
                member_member_event_preferences_content = io.TextIOWrapper(member_member_event_preferences.file, encoding='utf-8').read()
                reader = csv.reader(member_member_event_preferences_content.splitlines(), delimiter=',')
            except:
                raise forms.ValidationError("This is not a valid csv file.")

            for i, row in enumerate(reader):
                if not row:
                    continue
                # need at least 2 columns for member1 and member2
                if len(row) < 2:
                    raise forms.ValidationError(f"Row {i+1} has fewer than 2 columns. Each row needs at least member 1 and member 2.")
                member1_name = remove_punctuation(row[0], False)
                member2_name = remove_punctuation(row[1], False)
                # skip rows where both members are empty
                if member1_name == "" and member2_name == "":
                    continue
                if member1_name == "":
                    raise forms.ValidationError(f"Row {i+1} is missing a name in the first column.")
                if member2_name == "":
                    raise forms.ValidationError(f"Row {i+1} is missing a name in the second column.")
        return member_member_event_preferences_content
    
    def clean(self):
        cleaned_data = super().clean()
        max_events_per_member = cleaned_data.get("max_events_per_member")
        min_events_per_member = cleaned_data.get("min_events_per_member")
        if max_events_per_member is not None and min_events_per_member is not None:
            if max_events_per_member < min_events_per_member:
                raise forms.ValidationError("The maximum events per member cannot be smaller than the minimum events per member.")
        available_events = cleaned_data.get("available_events")
        conflicting_events = cleaned_data.get("conflicting_events")
        member_event_preferences_data = cleaned_data.get("member_event_preferences_data")
        member_member_event_preferences_data = cleaned_data.get("member_member_event_preferences_data")
        if conflicting_events and not available_events:
            self.add_error("conflicting_events", "You must upload Available Events to use Conflicting Events.")
        if member_member_event_preferences_data and not member_event_preferences_data:
            self.add_error("member_member_event_preferences_data", "You must upload Member Event Preferences to use Partner Preferences.")
        return cleaned_data


class CompetitionSettingsEditForm(ModelForm):

    class Meta:
        model = GeneratedCompetitionSettings
        fields = [
            "name",
            "notes",
            "max_events_per_member",
            "min_events_per_member",
            "skill_vs_preferences",
            "max_num_of_build_events_per_member",
            "use_ranking",
            "partner_preference_weight",
            "randomization",
        ]
        labels = {
            "name": "Name of upcoming competition",
            "skill_vs_preferences": "Event Preference Weight",
            "use_ranking": "Use Ranked Event Preferences",
            "partner_preference_weight": "Partner Preference Weight",
            "randomization": "Randomization",
        }
        help_texts = {
            "max_events_per_member": "The most events any single member can be assigned to.",
            "min_events_per_member": "The fewest events any single member can be assigned to. Must be at least 1.",
            "skill_vs_preferences": "How much weight to give event preferences when generating teams. 0 = ignore preferences (skill only), 1 = full weight on preferences.",
            "max_num_of_build_events_per_member": "The most build events any single member can be assigned to.",
            "use_ranking": "When enabled, higher-ranked preferences count more than lower-ranked ones. When disabled, all listed preferences are weighted equally.",
            "partner_preference_weight": "How much weight to give partner preferences (members wanting to be on the same event together). 0 = ignore, 1 = full weight.",
            "randomization": "Adds random noise to each member-event assignment score. 0 = no randomness (deterministic), 1 = maximum randomness. Uses a seeded RNG so regenerating produces the same result.",
        }
        widgets = {
            'notes': forms.Textarea(attrs={'cols': 20, 'rows': 5}),
            'skill_vs_preferences': forms.NumberInput(attrs={"type": "range", "min": 0, "max": 1, "value": 0.5}),
            'partner_preference_weight': forms.NumberInput(attrs={"type": "range", "min": 0, "max": 1, "step": 0.05, "value": 0.05}),
            'randomization': forms.NumberInput(attrs={"type": "range", "min": 0, "max": 1, "step": 0.05, "value": 0}),
        }

    def clean_skill_vs_preferences(self):
        skill_vs_preferences = self.cleaned_data.get("skill_vs_preferences")
        if skill_vs_preferences > 1 or skill_vs_preferences < 0:
            raise forms.ValidationError("Skill vs preferences should be between 0 and 1")
        return skill_vs_preferences
    def clean_partner_preference_weight(self):
        partner_preference_weight = self.cleaned_data.get("partner_preference_weight")
        if partner_preference_weight < 0 or partner_preference_weight > 1:
            raise forms.ValidationError("Partner preference weight should be between 0 and 1")
        return partner_preference_weight
    def clean_randomization(self):
        randomization = self.cleaned_data.get("randomization")
        if randomization < 0 or randomization > 1:
            raise forms.ValidationError("Randomization should be between 0 and 1")
        return randomization

    def clean_min_events_per_member(self):
        min_events_per_member = self.cleaned_data.get("min_events_per_member")
        if min_events_per_member < 1:
            raise forms.ValidationError("The minimum events per member cannot be smaller than 1.")
        return min_events_per_member
    
    def clean(self):
        max_events_per_member = self.cleaned_data.get("max_events_per_member")
        min_events_per_member = self.cleaned_data.get("min_events_per_member")
        if max_events_per_member < min_events_per_member:
            raise forms.ValidationError("The maximum events per member cannot be smaller than the minimum events per member.")
        return self.cleaned_data


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
        widgets = {
            'notes': forms.Textarea(attrs={'cols': 20, 'rows': 5}),
        }

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
        return team_size
    def clean_name(self):
        name = self.cleaned_data["name"]
        cleaned_name = remove_team_name_punctuation(name)
        if cleaned_name == "":
            raise forms.ValidationError("Team name is not valid.")
        return cleaned_name
    
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

        super(RequirementsForm, self).__init__(*args, **kwargs)
        # event_conflicts = kwargs.pop("event_conflicts")
        self.generated_team = generated_team
        self.requirements = requirements
        # self.events_with_3_members = events_with_3_members
        self.members_required_in_other_teams = members_required_in_other_teams
        # self.event_conflicts = event_conflicts
        self.fields["member"].queryset = member_queryset
        self.fields["event"].queryset = event_queryset
        self.fields["event"].empty_label = "None"
        self.fields["event"].required = False
        # super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data['member']
        event = cleaned_data['event']
        required_members = []
        events_to_members = {}
        generally_required_members = []
        for r in self.requirements:
            if r.member not in required_members:
                required_members.append(r.member)
            if r.event:
                if r.event not in events_to_members:
                    events_to_members[r.event] = [r.member]
                elif r.event in events_to_members:
                    events_to_members[r.event].append(r.member)
            else:
                generally_required_members.append(r.member)
        # if event_id:
        #     event = AvailableEvent.objects.get(id = event_id)
        # else:
        #     event = None
        
        # member = AvailableMember.objects.get(id = member_id)

        # new member would cause the team to go over the size limit
        if len(required_members) >= self.generated_team.team_size:
            raise forms.ValidationError("You have required too many members to be on the same team.")

        if member.is_senior and member not in required_members:
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
        if event in events_done_by_member or (event is None and member in generally_required_members):
            raise forms.ValidationError("This requirement already exists")
        
        
        if event is not None:
            # there is already enough members in the event
            if event in events_to_members:
                if len(events_to_members[event])>=2+int(event.needs_3_members):
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
                if e.conflict != None:
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


class AddEventForm(forms.Form):
    name = forms.CharField(max_length=200)
    needs_3_members = forms.BooleanField(required=False, label="3-person event")
    is_build_event = forms.BooleanField(required=False, label="Build event")

    def clean_name(self):
        name = self.cleaned_data['name']
        name = remove_punctuation(name, True)
        if not name:
            raise forms.ValidationError("Event name is not valid.")
        return name


class AddEventTypeForm(forms.Form):
    pass


class EventTypeColorForm(forms.Form):
    color = forms.CharField(max_length=7)


class AddMemberForm(forms.Form):
    name = forms.CharField(max_length=200)
    is_senior = forms.BooleanField(required=False, label="Senior")

    def clean_name(self):
        name = self.cleaned_data['name']
        name = remove_punctuation(name, False)
        if not name:
            raise forms.ValidationError("Member name is not valid.")
        return name


class AddPreferenceForm(forms.Form):
    event = forms.ModelChoiceField(queryset=AvailableEvent.objects.none())

    def __init__(self, *args, **kwargs):
        event_queryset = kwargs.pop('event_queryset', AvailableEvent.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['event'].queryset = event_queryset


class AddPartnerPreferenceForm(forms.Form):
    member1 = forms.ModelChoiceField(queryset=AvailableMember.objects.none(), label="Member 1")
    member2 = forms.ModelChoiceField(queryset=AvailableMember.objects.none(), label="Member 2")
    event = forms.ModelChoiceField(queryset=AvailableEvent.objects.none(), label="Event")

    def __init__(self, *args, **kwargs):
        member_queryset = kwargs.pop('member_queryset', AvailableMember.objects.none())
        event_queryset = kwargs.pop('event_queryset', AvailableEvent.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['member1'].queryset = member_queryset
        self.fields['member2'].queryset = member_queryset
        self.fields['event'].queryset = event_queryset

    def clean(self):
        cleaned_data = super().clean()
        member1 = cleaned_data.get('member1')
        member2 = cleaned_data.get('member2')
        if member1 and member2 and member1 == member2:
            raise forms.ValidationError("Member 1 and Member 2 must be different.")
        return cleaned_data


class AddConflictGroupForm(forms.Form):
    pass


class AddEventToConflictForm(forms.Form):
    event = forms.ModelChoiceField(queryset=AvailableEvent.objects.none())

    def __init__(self, *args, **kwargs):
        event_queryset = kwargs.pop('event_queryset', AvailableEvent.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['event'].queryset = event_queryset

