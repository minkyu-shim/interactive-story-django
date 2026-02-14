from django import forms
from .models import StoryRatingComment

class StoryRatingCommentForm(forms.ModelForm):
    class Meta:
        model = StoryRatingComment
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.HiddenInput(),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your comment here...'}),
        }
