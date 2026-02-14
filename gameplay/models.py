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
    story_source = models.CharField(max_length=255, db_index=True, default='')
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'story_source', 'story_id')

    def __str__(self):
        return f"{self.user.username} rated Story {self.story_id} [{self.story_source}]: {self.rating}/5"


class StoryReport(models.Model):
    class Reason(models.TextChoices):
        SPAM = 'spam', 'Spam'
        ABUSE = 'abuse', 'Abusive content'
        SEXUAL = 'sexual_content', 'Sexual content'
        VIOLENCE = 'violence', 'Violence'
        HATE = 'hate', 'Hate speech'
        MISINFORMATION = 'misinformation', 'Misinformation'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_REVIEW = 'in_review', 'In review'
        RESOLVED = 'resolved', 'Resolved'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_reports')
    story_id = models.IntegerField(db_index=True)
    story_title_snapshot = models.CharField(max_length=200, blank=True)
    reason = models.CharField(max_length=32, choices=Reason.choices)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    admin_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_story_reports',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'story_id')

    def __str__(self):
        return f"Report by {self.user.username} on story {self.story_id} ({self.reason})"
