from django.shortcuts import render
from .services import get_stories

def story_list(request):
    # Fetch stories from the Flask API to here
    stories = get_stories()
    # Send them to the 'story_list.html' template
    return render(request, 'gameplay/story_list.html', {'stories': stories})