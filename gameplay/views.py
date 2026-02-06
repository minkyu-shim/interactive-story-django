from django.shortcuts import render, redirect
from .models import Play
from .services import get_stories, get_story_start, get_node
from django.db.models import Count


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
    node_data = get_node(story_id, node_id)

    if not node_data:
        return redirect('story_list')

    # Our actual story is is_game_over however seed for test case uses is_ending. I'll do this to make it both work
    is_actually_ending = (
            node_data.get('type') == 'ending' or
            node_data.get('is_game_over') or
            node_data.get('is_ending')
    )
    # --- FIX END ---

    if is_actually_ending:
        # 1. Save the Play Record
        try:
            Play.objects.create(
                story_id=story_id,
                ending_node_id=node_data.get('id', node_id)
            )
            print(f"Ending reached: {node_data.get('id')}")
        except Exception as e:
            print(f"Save Error: {e}")

    # 2. Pass the 'is_actually_ending' flag to the template explicitly
    return render(request, 'gameplay/play_page.html', {
        'node': node_data,
        'story_id': story_id,
        'is_ending': is_actually_ending  # Overwrite the confusion
    })


def global_stats(request):
    """Level 13: Display play statistics."""
    # Count how many times each ending_node_id appears
    # Result example: [{'ending_node_id': 'bad_ending', 'count': 5}, ...]
    ending_stats = Play.objects.values('ending_node_id').annotate(count=Count('ending_node_id')).order_by('-count')

    total_plays = Play.objects.count()

    return render(request, 'gameplay/stats.html', {
        'total_plays': total_plays,
        'ending_stats': ending_stats
    })
