from django.shortcuts import render, redirect
from .models import Play
from .services import get_stories, get_story_start, get_node


def story_list(request):
    stories = get_stories()
    if stories is None:
        return render(request, 'gameplay/waking_up.html')
    return render(request, 'gameplay/story_list.html', {'stories': stories})


def start_story(request, story_id):
    """Finds the start node and redirects to the play view."""
    start_node = get_story_start(story_id)
    if start_node:
        # Use the 'id' (custom_id) from the API response to build the URL
        return redirect('play_node', story_id=story_id, node_id=start_node['id'])
    return redirect('story_list')


def play_node(request, story_id, node_id):
    """Main gameplay view for a specific node."""
    node_data = get_node(story_id, node_id)

    if not node_data:
        return redirect('story_list')

    # Logic: If it's an ending, save the Play record
    if node_data.get('is_ending'):
        Play.objects.create(
            story_id=story_id,
            ending_page_id=0  # We can't save string ID in IntegerField, just put 0 or update Model
        )

    # Pass story_id to the template so we can build links for choices
    return render(request, 'gameplay/play_page.html', {
        'node': node_data,
        'story_id': story_id
    })