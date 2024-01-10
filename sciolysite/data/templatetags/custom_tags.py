from django import template

register = template.Library()

@register.filter
def index(sequence, position):
    # print("hi2 ")
    # print(sequence)
    # print(position)
    return sequence[int(position)]
