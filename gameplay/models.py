from django.db import models


class Play(models.Model):
    story_id = models.IntegerField()  # Story ID is still an Integer (Database ID)

    ending_node_id = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Story {self.story_id} ended at {self.ending_node_id}"


class PlaySession(models.Model):
    session_key = models.CharField(max_length=40)

    story_id = models.IntegerField()

    current_node_id = models.CharField(max_length=50)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session_key', 'story_id')

    def __str__(self):
        return f"Session {self.session_key} - Story {self.story_id} at {self.current_node_id}"
