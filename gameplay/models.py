from django.db import models
from django.contrib.auth.models import User


class Play(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plays', null=True, blank=True)
    story_id = models.IntegerField()
    ending_node_id = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - Story {self.story_id} ended at {self.ending_node_id}"


class StoryOwnership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_stories')
    story_id = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.user.username} owns Story {self.story_id}"


class PlaySession(models.Model):
    session_key = models.CharField(max_length=40)

    story_id = models.IntegerField()

    current_node_id = models.CharField(max_length=50)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session_key', 'story_id')

    def __str__(self):
        return f"Session {self.session_key} - Story {self.story_id} at {self.current_node_id}"
