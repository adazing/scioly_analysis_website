from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Competition)
admin.site.register(Team)
admin.site.register(EventMemberInstance)
admin.site.register(Member)
admin.site.register(EventMemberPracticeInstance)
admin.site.register(Practice)