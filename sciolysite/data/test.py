import string
from difflib import SequenceMatcher


def remove_punctuation(input_string):
    input_string=input_string.lower().strip()
    # Make a translator object to replace punctuation with none
    translator = str.maketrans('', '', string.punctuation)
    # Use the translator
    return input_string.translate(translator)

print(remove_punctuation("Write it, Do it"))

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

print(similar("albert ming wei", "ming wei"))
print(similar("sarah kobi","sarah kung"))
# print(similar("Ada Langford"))