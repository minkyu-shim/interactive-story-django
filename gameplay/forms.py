from django import forms
from .models import StoryRatingComment, StoryReport

class StoryRatingCommentForm(forms.ModelForm):
    class Meta:
        model = StoryRatingComment
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.HiddenInput(),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your comment here...'}),
        }


class StoryReportForm(forms.ModelForm):
    class Meta:
        model = StoryReport
        fields = ['reason', 'details']
        widgets = {
            'reason': forms.Select(),
            'details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Add extra details (optional).'}),
        }


class StoryReportModerationForm(forms.ModelForm):
    class Meta:
        model = StoryReport
        fields = ['status', 'admin_note']
        widgets = {
            'status': forms.Select(),
            'admin_note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Internal note for moderators.'}),
        }
