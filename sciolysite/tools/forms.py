from django import forms
import csv
import io

def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.lower().replace("&", "and").replace("(B)", "").replace("(3)", "") if c.isalpha() or c==" "])
    else:
        input_string="".join([c for c in input_string.replace("(S)","").replace("(O)","").replace("(R)","").lower() if c.isalpha() or c==" "])
    return input_string.strip().title()


# class TeamForm(ModelForm):
    # # SHOULD VALIDATE AND PUT ATTRS THING ON OTHER STUFF ARMITA PLS REMIND ME
    # score_data = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}), label="Score CSV data")
    # class Meta:
    #     model = Team
    #     fields = [
    #         "name"
    #     ]
    #     labels = {
    #         "name": "Name of Team"
    #     }
    # def clean_score_data(self, *args, **kwargs):
    #     score_data = self.cleaned_data.get("score_data")
        
    #     # check if ending is csv file
    #     if not score_data.name.endswith(".csv"):
    #         raise forms.ValidationError("This is not a valid csv file.")
        
    #     # try to read the file and validate
    #     try:
    #         score_data.seek(0)  # Reset file pointer to start
    #         score_data_content = io.TextIOWrapper(score_data.file, encoding='utf-8').read()
    #         reader = csv.reader(score_data_content.splitlines(), delimiter=',')
    #         next(reader)  # Skip header
    #     except:
    #         raise forms.ValidationError("This is not a valid csv file.")
    #     done_events = []
    #     for i, row in enumerate(reader):
    #         # see if row length is changes --> tampering with file?
    #         if i==0:
    #             row_length=len(row)
    #         elif len(row)!=row_length:
    #             raise forms.ValidationError("This is not a valid csv file.")
            
    #         # see if score is an int
    #         try:
    #             score = int(row[4].strip())
    #         except:
    #             raise forms.ValidationError("Some of the scores are non-integer values.")
            
    #         # if event_name is blank, means reached end of file
    #         event_name=row[0]
    #         event_name = remove_punctuation(event_name, True)
    #         if event_name!="":
    #             if event_name in done_events:
    #                 raise forms.ValidationError("There are some event repeats.")
    #             is_at_least_one_member_on_event = False
    #             for m in range(1,4):
    #                 member_name = remove_punctuation(row[m], False)
    #                 if member_name!="":
    #                     is_at_least_one_member_on_event =True
    #             if not is_at_least_one_member_on_event:
    #                 raise forms.ValidationError("One of the events has no people on it.")
    #             done_events.append(event_name)
    #         else: # reached end
    #             break
    #     return score_data_content


class ConflictCheckingForm(forms.Form):
    team_data = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}))
    conflicting_events = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}))
    # File Structure:
    # Event1,Event2,Event4 <--- these are conflict times, all the events in each row conflict each other (are in the same timeblock)
    # Event3,Event7,
    # ...
    
    
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
            num_rows = 0
            for i, row in enumerate(reader):
                # check if row length changes --> tampering with file?
                if i==0:
                    row_length=len(row)
                elif len(row)!=row_length:
                    raise forms.ValidationError("This is not a valid csv file.")
                
                # check if first cell of row have event.
                if remove_punctuation(row[0], True)=="":
                    raise forms.ValidationError("One of the rows has no event in the first cell.")
                # check for repeats
                for e in row:
                    event_name = remove_punctuation(e, True)
                    if event_name != "":
                        if event_name in list_of_events:
                            raise forms.ValidationError("Some of the events are repeated!")
                        list_of_events.append(event_name)
                num_rows += 1
            
            if num_rows == 0:
                raise forms.ValidationError("File is empty!")

        return conflicting_events_content
    
    def clean_team_data(self, *args, **kwargs):
        team_data = self.cleaned_data.get("team_data")
        
        # check if ending is csv file
        if not team_data.name.endswith(".csv"):
            raise forms.ValidationError("This is not a valid csv file.")
        
        # try to read the file and validate
        try:
            team_data.seek(0)  # Reset file pointer to start
            score_data_content = io.TextIOWrapper(team_data.file, encoding='utf-8').read()
            reader = csv.reader(score_data_content.splitlines(), delimiter=',')
            # next(reader)  # Skip header
        except:
            raise forms.ValidationError("This is not a valid csv file.")
        done_events = []
        num_rows = 0
        for i, row in enumerate(reader):
            # see if row length is changes --> tampering with file?
            if i==0:
                row_length=len(row)
                if row_length < 2:
                    raise forms.ValidationError("This file isn't formatted correctly (found row with length 1, when minimum row length should be 2).")
                if row_length > 4:
                    raise forms.ValidationError("This file isn't formatted correctly (found row with length greater than 4, when maximum row length should be 4).")

            elif len(row)!=row_length:
                raise forms.ValidationError("This is not a valid csv file.")

            # if event_name is blank, means reached end of file
            event_name=row[0]
            event_name = remove_punctuation(event_name, True)
            if event_name!="":
                if event_name in done_events:
                    raise forms.ValidationError("There are some event repeats.")
                is_at_least_one_member_on_event = False
                for m in range(1,min(row_length, 4)):
                    member_name = remove_punctuation(row[m], False)
                    if member_name!="":
                        is_at_least_one_member_on_event =True
                if not is_at_least_one_member_on_event:
                    raise forms.ValidationError("One of the events has no people on it.")
                done_events.append(event_name)
            else: # reached end
                break
            num_rows += 1
        
        if num_rows == 0:
            raise forms.ValidationError("File is empty!")

        return score_data_content



# class TeamForm(forms.Form):
#     conflicting_events = forms.FileField(required=True, attrs={"accept": ".csv"})
#     score_data = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}))
#     def clean_score_data(self, *args, **kwargs):
#         score_data = self.cleaned_data.get("score_data")
        
#         # check if ending is csv file
#         if not score_data.name.endswith(".csv"):
#             raise forms.ValidationError("This is not a valid csv file.")
        
#         # try to read the file and validate
#         try:
#             score_data.seek(0)  # Reset file pointer to start
#             score_data_content = io.TextIOWrapper(score_data.file, encoding='utf-8').read()
#             reader = csv.reader(score_data_content.splitlines(), delimiter=',')
#             # next(reader)  # Skip header
#         except:
#             raise forms.ValidationError("This is not a valid csv file.")
        
#         for i, row in enumerate(reader):
#             # see if row length is changes --> tampering with file?
#             if i==0:
#                 row_length=len(row)
#             elif len(row)!=row_length:
#                 raise forms.ValidationError("This is not a valid csv file.")
            
#             # see if score is an int
#             # try:
#             #     score = int(row[4].strip())
#             # except:
#             #     raise forms.ValidationError("Some of the scores are non-integer values.")
            
#             # if event_name is blank, means reached end of file drugs are great
#             event_name=row[0]
#             event_name = remove_punctuation(event_name, True)
#             if event_name!="":
                
#                 is_at_least_one_member_on_event = False
#                 for m in range(1,4):
#                     member_name = remove_punctuation(row[m], False)
#                     if member_name!="":
#                         is_at_least_one_member_on_event =True
#                 if not is_at_least_one_member_on_event:
#                     raise forms.ValidationError("One of the events has no people on it.")
#             else: # reached end
#                 break
#         return score_data_content




