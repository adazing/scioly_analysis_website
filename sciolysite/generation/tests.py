from django.test import TestCase

# Create your tests here.

def remove_punctuation(input_string, is_event): # make it so only allow for letters and spaces
    input_string = str(input_string)
    if is_event:
        input_string="".join([c for c in input_string.lower().replace("trial", "").replace("&", "and").replace("(3)","").replace("(*)","") if c.isalpha() or c==" "])
    else:
        print("hi")
        input_string="".join([c for c in input_string.replace("(S)","").replace("(O)","").replace("(R)","").lower() if c.isalpha() or c==" "])
    return input_string.strip().title()

print(remove_punctuation("Brian Zhao (O)", False))
# print("Brian Zhao (O)".replace("(O)",""))

dictionary = sorted({"a":1, "b":1, "d":1, "c":1}.items(), key=lambda item: item[1])
print(dictionary)