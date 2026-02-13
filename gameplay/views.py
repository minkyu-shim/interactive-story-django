from django.shortcuts import render, redirect, get_object_or_404
from .models import Play, PlaySession
from .services import (
    get_stories, get_story_start, get_node, get_story_details,
    create_story, update_story, delete_story, create_page, create_choice
)
from django.db.models import Count


def story_list(request):
    # Capture search and filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'published')
    
    params = {}
    if status_filter:
        params['status'] = status_filter

    # Fetch stories from API (using status filter if supported)
    stories = get_stories(params=params)
    
    if stories is None:
        return render(request, 'gameplay/waking_up.html')

    # Client-side fallback: Filter by title if the API didn't do it
    if search_query:
        query = search_query.lower()
        stories = [
            s for s in stories 
            if query in s.get('title', '').lower() 
            or query in s.get('description', '').lower()
        ]

    # Level 13: Check for active sessions to allow resuming
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    
    active_sessions = PlaySession.objects.filter(session_key=session_key).values_list('story_id', 'current_node_id')
    resume_map = {story_id: node_id for story_id, node_id in active_sessions}

    for story in stories:
        story['resume_node'] = resume_map.get(story['id'])
        
    return render(request, 'gameplay/story_list.html', {
        'stories': stories,
        'search_query': search_query,
        'status_filter': status_filter
    })


def start_story(request, story_id):
    """Finds the start node and redirects to the play view."""
    # Level 13: If a session exists, we might want to clear it if they click "Start Over"
    # But usually start_story is for a fresh start.
    if not request.session.session_key:
        request.session.create()
    PlaySession.objects.filter(session_key=request.session.session_key, story_id=story_id).delete()

    start_node = get_story_start(story_id)
    if start_node:
        return redirect('play_node', story_id=story_id, node_id=start_node['id'])
    return redirect('story_list')


def play_node(request, story_id, node_id):
    node_data = get_node(story_id, node_id)

    if not node_data:
        return redirect('story_list')

    # Ensure session exists
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    # Our actual story is is_game_over however seed for test case uses is_ending.
    is_actually_ending = (
            node_data.get('type') == 'ending' or
            node_data.get('is_game_over') or
            node_data.get('is_ending')
    )

    if is_actually_ending:
        # 1. Save the Play Record
        try:
            Play.objects.create(
                story_id=story_id,
                ending_node_id=node_data.get('id', node_id)
            )
            # 2. Clear the PlaySession because the story ended
            PlaySession.objects.filter(session_key=session_key, story_id=story_id).delete()
        except Exception as e:
            print(f"Save Error: {e}")
    else:
        # Level 13: Auto-save progression
        PlaySession.objects.update_or_create(
            session_key=session_key,
            story_id=story_id,
            defaults={'current_node_id': node_id}
        )

    return render(request, 'gameplay/play_page.html', {
        'node': node_data,
        'story_id': story_id,
        'is_ending': is_actually_ending
    })

def global_stats(request):
    """Level 10: Display play statistics grouped by story."""
    # Get all stories to map IDs to titles
    stories_data = get_stories()
    story_map = {s['id']: s['title'] for s in stories_data} if stories_data else {}

    # Group plays by story_id
    story_stats = Play.objects.values('story_id').annotate(total_plays=Count('id')).order_by('-total_plays')

    # For each story, get ending distribution
    for stat in story_stats:
        stat['story_title'] = story_map.get(stat['story_id'], f"Unknown Story ({stat['story_id']})")
        stat['endings'] = Play.objects.filter(story_id=stat['story_id']).values('ending_node_id').annotate(
            count=Count('id')).order_by('-count')

    total_plays = Play.objects.count()

    return render(request, 'gameplay/stats.html', {
        'total_plays': total_plays,
        'story_stats': story_stats
    })


def create_story_view(request):
    """View to create a new story."""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        status = 'published'  # Level 10: All stories are published

        data = {
            'title': title,
            'description': description,
            'status': status
        }

        new_story = create_story(data)
        if new_story:
            return redirect('edit_story', story_id=new_story['id'])

    return render(request, 'gameplay/story_form.html', {'action': 'Create'})


def edit_story_view(request, story_id):
    """View to edit a story and its pages."""
    story = get_story_details(story_id)
    if not story:
        return redirect('story_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        data = {
            'title': title,
            'description': description,
            'status': story.get('status', 'published')
        }

        update_story(story_id, data)
        return redirect('edit_story', story_id=story_id)

    return render(request, 'gameplay/story_edit.html', {'story': story})


def delete_story_view(request, story_id):
    """View to delete a story."""
    if request.method == 'POST':
        if delete_story(story_id):
            return redirect('story_list')
    return render(request, 'gameplay/story_confirm_delete.html', {'story_id': story_id})


def add_page_view(request, story_id):
    """View to add a page to a story."""
    if request.method == 'POST':
        text = request.POST.get('text')
        is_ending = request.POST.get('is_ending') == 'on'
        ending_label = request.POST.get('ending_label')

        data = {
            'text': text,
            'is_ending': is_ending,
            'ending_label': ending_label if is_ending else None
        }

        create_page(story_id, data)
        return redirect('edit_story', story_id=story_id)

    return render(request, 'gameplay/page_form.html', {'story_id': story_id})


def add_choice_view(request, story_id, page_id):
    """View to add a choice to a page."""
    if request.method == 'POST':
        text = request.POST.get('text')
        next_page_id = request.POST.get('next_page_id')

        data = {
            'text': text,
            'next_page_id': next_page_id
        }

        create_choice(page_id, data)
        return redirect('edit_story', story_id=story_id)

    # We need the list of pages to choose the next_page_id
    story = get_story_details(story_id)
    pages = story.get('pages', [])

    return render(request, 'gameplay/choice_form.html', {
        'story_id': story_id,
        'page_id': page_id,
        'pages': pages
    })
