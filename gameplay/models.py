from django.db import models

class Play(models.Model):
    # The ID of the story from the Flask database
    story_id = models.IntegerField()
    # The ID of the ending page reached
    ending_page_id = models.IntegerField()
    # Timestamp of when the player reached the ending
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Story {self.story_id} finished at {self.created_at}"