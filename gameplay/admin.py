from django.contrib import admin
from .models import Play, StoryOwnership, PlaySession, StoryRatingComment

admin.site.register(Play)
admin.site.register(StoryOwnership)
admin.site.register(PlaySession)
admin.site.register(StoryRatingComment)
