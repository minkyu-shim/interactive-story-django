from django.shortcuts import render
from .services import get_stories, get_page, get_story_start
from django.shortcuts import redirect
from .models import Play

def story_list(request):
    # Fetch stories from the Flask API to here
    stories = get_stories()
    # Send them to the 'story_list.html' template
    return render(request, 'gameplay/story_list.html', {'stories': stories})


def play_page(request, page_id):
    page_data = get_page(page_id)

    if not page_data:
        return redirect('story_list')

    # Level 10: If it's an ending, save a Play record
    if page_data.get('is_ending'):
        Play.objects.create(
            story_id=0,  # We'll refine how to track the current story ID later
            ending_page_id=page_id
        )

    return render(request, 'gameplay/play_page.html', {'page': page_data})

def start_story(request, story_id):
    start_page = get_story_start(story_id)
    if start_page:
         # Redirect to our play_page view with the correct ID
        return redirect('play_page', page_id=start_page['id'])
    return redirect('story_list')