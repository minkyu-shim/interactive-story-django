from django.db import models
from django.contrib.auth.models import User


class Play(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plays', null=True, blank=True)
    story_id = models.IntegerField()
    ending_node_id = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        username = self.user.username if self.user_id else "Anonymous"
        return f"{username} - Story {self.story_id} ended at {self.ending_node_id}"


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


class StoryRatingComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_comments')
    story_id = models.IntegerField()
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'story_id')

    def __str__(self):
        return f"{self.user.username} rated Story {self.story_id}: {self.rating}/5"
