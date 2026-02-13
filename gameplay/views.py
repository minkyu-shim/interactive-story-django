from django.shortcuts import render, redirect, get_object_or_404
from .models import Play, PlaySession
from .services import (
    get_stories, get_story_start, get_node, get_story_details,
    create_story, update_story, delete_story, create_page, create_choice
)
from django.db.models import Count


def story_list(request):
    """Public Reader View: Only shows published stories."""
    search_query = request.GET.get('search', '')

    # Strictly enforce published status for public list
    params = {'status': 'published'}

    stories = get_stories(params=params)

    if stories is None:
        return render(request, 'gameplay/waking_up.html')

    if search_query:
        query = search_query.lower()
        stories = [
            s for s in stories
            if query in s.get('title', '').lower()
               or query in s.get('description', '').lower()
        ]

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
        'view_mode': 'reader'
    })


def author_dashboard(request):
    """Author View: Shows all stories including drafts."""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')  # Allow filtering by any status here

    params = {}
    if status_filter:
        params['status'] = status_filter

    stories = get_stories(params=params)

    if stories is None:
        return render(request, 'gameplay/waking_up.html')

    if search_query:
        query = search_query.lower()
        stories = [
            s for s in stories
            if query in s.get('title', '').lower()
               or query in s.get('description', '').lower()
        ]

    return render(request, 'gameplay/story_list.html', {
        'stories': stories,
        'search_query': search_query,
        'status_filter': status_filter,
        'view_mode': 'author'
    })


def start_story(request, story_id):
    """Finds the start node and redirects to the play view."""
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

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    is_actually_ending = (
            node_data.get('type') == 'ending' or
            node_data.get('is_game_over') or
            node_data.get('is_ending')
    )

    # Fetch story details to check status for "Preview Mode" (no stats for drafts)
    story_details = get_story_details(story_id)
    is_preview = story_details.get('status') == 'draft' if story_details else False

    if is_actually_ending:
        if not is_preview:
            # Save the Play Record only if NOT a draft
            try:
                Play.objects.create(
                    story_id=story_id,
                    ending_node_id=node_data.get('id', node_id)
                )
            except Exception as e:
                print(f"Save Error: {e}")

        # Clear the PlaySession regardless
        PlaySession.objects.filter(session_key=session_key, story_id=story_id).delete()
    else:
        # Auto-save progression
        PlaySession.objects.update_or_create(
            session_key=session_key,
            story_id=story_id,
            defaults={'current_node_id': node_id}
        )

    return render(request, 'gameplay/play_page.html', {
        'node': node_data,
        'story_id': story_id,
        'is_ending': is_actually_ending,
        'is_preview': is_preview
    })


def global_stats(request):
    """Level 13: Display play statistics with named endings and percentages."""

    stories_data = get_stories()

    story_map = {s['id']: s for s in stories_data} if stories_data else {}

    story_stats = Play.objects.values('story_id').annotate(total_plays=Count('id')).order_by('-total_plays')

    for stat in story_stats:

        story_id = stat['story_id']

        story_info = story_map.get(story_id, {})

        stat['story_title'] = story_info.get('title', f"Unknown Story ({story_id})")

        # Fetch story details to get page labels

        full_story = get_story_details(story_id)

        label_map = {}

        if full_story and 'pages' in full_story:
            label_map = {str(p['id']): p.get('ending_label') for p in full_story['pages'] if p.get('is_ending')}

        endings = Play.objects.filter(story_id=story_id).values('ending_node_id').annotate(count=Count('id')).order_by(
            '-count')

        stat_endings = []

        for e in endings:
            eid = str(e['ending_node_id'])

            percentage = (e['count'] / stat['total_plays'] * 100) if stat['total_plays'] > 0 else 0

            stat_endings.append({

                'id': eid,

                'label': label_map.get(eid, f"Ending {eid}"),

                'count': e['count'],

                'percentage': round(percentage, 1)

            })

        stat['endings'] = stat_endings

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
