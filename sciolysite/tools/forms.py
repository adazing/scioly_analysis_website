from django import forms
import csv
import io

class Team_Form(forms.Form):
    conflicting_events = forms.FileField(required=True, attrs={"accept": ".csv"})
    score_data = forms.FileField(widget=forms.FileInput(attrs={"accept": ".csv"}))
    def clean_score_data(self, *args, **kwargs):
        score_data = self.cleaned_data.get("score_data")
        
        # check if ending is csv file
        if not score_data.name.endswith(".csv"):
            raise forms.ValidationError("This is not a valid csv file.")
        
        # try to read the file and validate
        try:
            score_data.seek(0)  # Reset file pointer to start
            score_data_content = io.TextIOWrapper(score_data.file, encoding='utf-8').read()
            reader = csv.reader(score_data_content.splitlines(), delimiter=',')
            next(reader)  # Skip header
        except:
            raise forms.ValidationError("This is not a valid csv file.")
        
        for i, row in enumerate(reader):
            # see if row length is changes --> tampering with file?
            if i==0:
                row_length=len(row)
            elif len(row)!=row_length:
                raise forms.ValidationError("This is not a valid csv file.")
            
            # see if score is an int
            # try:
            #     score = int(row[4].strip())
            # except:
            #     raise forms.ValidationError("Some of the scores are non-integer values.")
            
            # if event_name is blank, means reached end of file drugs are great
            event_name=row[0]
            event_name = remove_punctuation(event_name, True)
            if event_name!="":
                
                is_at_least_one_member_on_event = False
                for m in range(1,4):
                    member_name = remove_punctuation(row[m], False)
                    if member_name!="":
                        is_at_least_one_member_on_event =True
                if not is_at_least_one_member_on_event:
                    raise forms.ValidationError("One of the events has no people on it.")
            else: # reached end
                break
        return score_data_content




