from django.contrib import admin
from django.utils import timezone

from .models import Play, StoryOwnership, PlaySession, StoryRatingComment, StoryReport

admin.site.register(Play)
admin.site.register(StoryOwnership)
admin.site.register(PlaySession)
admin.site.register(StoryRatingComment)


@admin.register(StoryReport)
class StoryReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'story_id', 'story_title_snapshot', 'user', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('story_id', 'story_title_snapshot', 'user__username', 'details')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
    actions = ('mark_in_review', 'mark_resolved', 'mark_rejected')

    @admin.action(description='Mark selected reports as in review')
    def mark_in_review(self, request, queryset):
        queryset.update(status=StoryReport.Status.IN_REVIEW, resolved_by=None, resolved_at=None)

    @admin.action(description='Mark selected reports as resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(status=StoryReport.Status.RESOLVED, resolved_by=request.user, resolved_at=timezone.now())

    @admin.action(description='Mark selected reports as rejected')
    def mark_rejected(self, request, queryset):
        queryset.update(status=StoryReport.Status.REJECTED, resolved_by=request.user, resolved_at=timezone.now())
