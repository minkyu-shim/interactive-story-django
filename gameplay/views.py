import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.exceptions import PermissionDenied
from .models import Play, PlaySession, StoryOwnership, StoryRatingComment
from .forms import StoryRatingCommentForm
from .services import (
    get_stories, get_story_start, get_node, get_story_details,
    create_story, update_story, delete_story, create_page, create_choice,
    update_page, delete_page, update_choice, delete_choice, get_story_nodes
)
from django.db.models import Count, Avg

logger = logging.getLogger(__name__)
VALID_STORY_STATUSES = {'draft', 'published', 'suspended'}


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

    # Add average ratings
    rating_stats = StoryRatingComment.objects.values('story_id').annotate(avg_rating=Avg('rating'), count=Count('id'))
    rating_map = {item['story_id']: item for item in rating_stats}

    for story in stories:
        story['resume_node'] = resume_map.get(story['id'])
        stats = rating_map.get(story['id'], {'avg_rating': 0, 'count': 0})
        story['avg_rating'] = round(stats['avg_rating'], 1) if stats['avg_rating'] else 0
        story['rating_count'] = stats['count']

    return render(request, 'gameplay/story_list.html', {
        'stories': stories,
        'search_query': search_query,
        'view_mode': 'reader'
    })


def signup(request):
    """Level 16: User registration."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('story_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def author_dashboard(request):
    """Author View: Shows all stories including drafts. Admins see everything, authors see their own."""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')  # Allow filtering by any status here

    params = {}
    if status_filter:
        params['status'] = status_filter

    stories = get_stories(params=params)

    if stories is None:
        return render(request, 'gameplay/waking_up.html')

    # Level 16: Ownership filtering
    if not request.user.is_staff:
        owned_ids = StoryOwnership.objects.filter(user=request.user).values_list('story_id', flat=True)
        stories = [s for s in stories if s['id'] in owned_ids]

    if search_query:
        query = search_query.lower()
        stories = [
            s for s in stories
            if query in s.get('title', '').lower()
               or query in s.get('description', '').lower()
        ]

    # Add average ratings
    rating_stats = StoryRatingComment.objects.values('story_id').annotate(avg_rating=Avg('rating'), count=Count('id'))
    rating_map = {item['story_id']: item for item in rating_stats}

    for story in stories:
        stats = rating_map.get(story['id'], {'avg_rating': 0, 'count': 0})
        story['avg_rating'] = round(stats['avg_rating'], 1) if stats['avg_rating'] else 0
        story['rating_count'] = stats['count']

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

    ratings_comments = []
    user_rating_form = None
    if is_actually_ending:
        if not is_preview:
            # Save the Play Record only if NOT a draft
            try:
                Play.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    story_id=story_id,
                    ending_node_id=node_data.get('id', node_id)
                )
            except Exception:
                logger.exception(
                    "Failed to save play record for story_id=%s ending_node_id=%s",
                    story_id,
                    node_data.get('id', node_id),
                )

        # Clear the PlaySession regardless
        PlaySession.objects.filter(session_key=session_key, story_id=story_id).delete()

        # Get ratings and comments
        ratings_comments = StoryRatingComment.objects.filter(story_id=story_id).order_by('-created_at')
        if request.user.is_authenticated:
            existing_rating = StoryRatingComment.objects.filter(user=request.user, story_id=story_id).first()
            if existing_rating:
                user_rating_form = StoryRatingCommentForm(instance=existing_rating)
            else:
                user_rating_form = StoryRatingCommentForm()
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
        'is_preview': is_preview,
        'ratings_comments': ratings_comments,
        'user_rating_form': user_rating_form
    })


@login_required
def submit_rating_comment(request, story_id):
    if request.method == 'POST':
        existing_rating = StoryRatingComment.objects.filter(user=request.user, story_id=story_id).first()
        if existing_rating:
            form = StoryRatingCommentForm(request.POST, instance=existing_rating)
        else:
            form = StoryRatingCommentForm(request.POST)

        if form.is_valid():
            rating_comment = form.save(commit=False)
            rating_comment.user = request.user
            rating_comment.story_id = story_id
            rating_comment.save()

    return redirect(request.META.get('HTTP_REFERER', 'story_list'))


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


@login_required
def create_story_view(request):
    """View to create a new story."""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        status = request.POST.get('status', 'draft')
        if status not in VALID_STORY_STATUSES:
            status = 'draft'

        data = {
            'title': title,
            'description': description,
            'status': status
        }

        new_story = create_story(data)
        if new_story:
            # Level 16: Save ownership
            StoryOwnership.objects.create(user=request.user, story_id=new_story['id'])
            return redirect('edit_story', story_id=new_story['id'])

    return render(request, 'gameplay/story_form.html', {'action': 'Create'})


def check_ownership(user, story_id):
    """Helper to check if a user owns a story or is admin."""
    if user.is_staff:
        return True
    return StoryOwnership.objects.filter(user=user, story_id=story_id).exists()


def get_story_with_pages(story_id):
    story = get_story_details(story_id)
    if not story:
        return None
    story['pages'] = story.get('pages') or get_story_nodes(story_id) or []
    return story


def find_page(story, page_id):
    return next((p for p in story.get('pages', []) if str(p.get('id')) == str(page_id)), None)


def find_choice(story, choice_id):
    for page in story.get('pages', []):
        choice = next((c for c in page.get('choices', []) if str(c.get('id')) == str(choice_id)), None)
        if choice:
            return page, choice
    return None, None


@login_required
def edit_story_view(request, story_id):
    """View to edit a story and its pages."""
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    story = get_story_with_pages(story_id)
    if not story:
        return redirect('story_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        status = request.POST.get('status', story.get('status', 'published'))
        if status not in VALID_STORY_STATUSES:
            status = story.get('status', 'published')

        data = {
            'id': story_id,
            'title': title,
            'description': description,
            'status': status
        }

        updated_story = update_story(story_id, data)
        if updated_story is None:
            logger.warning("Story update failed for story_id=%s", story_id)
        elif str(updated_story.get('id')) != str(story_id):
            logger.error(
                "Story update returned mismatched id: requested=%s returned=%s",
                story_id,
                updated_story.get('id'),
            )
        return redirect('edit_story', story_id=story_id)

    return render(request, 'gameplay/story_edit.html', {'story': story})


@login_required
def delete_story_view(request, story_id):
    """View to delete a story."""
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    if request.method == 'POST':
        if delete_story(story_id):
            StoryOwnership.objects.filter(story_id=story_id).delete()
            return redirect('story_list')
    return render(request, 'gameplay/story_confirm_delete.html', {'story_id': story_id})


@login_required
def add_page_view(request, story_id):
    """View to add a page to a story."""
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    if request.method == 'POST':
        text = request.POST.get('text')
        is_ending = request.POST.get('is_ending') == 'on'
        ending_label = request.POST.get('ending_label')

        import uuid
        data = {
            'title': f"Node {uuid.uuid4().hex[:6]}",  # Add a title
            'custom_id': f"node_{uuid.uuid4().hex[:8]}", # Add a custom_id
            'text': text,
            'is_ending': is_ending,
            'ending_label': ending_label if is_ending else None
        }

        create_page(story_id, data)
        return redirect('edit_story', story_id=story_id)

    return render(request, 'gameplay/page_form.html', {'story_id': story_id})


@login_required
def add_choice_view(request, story_id, page_id):
    """View to add a choice to a page."""
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    story = get_story_with_pages(story_id)
    if not story:
        return redirect('story_list')
    page = find_page(story, page_id)
    if not page:
        raise PermissionDenied

    if request.method == 'POST':
        text = request.POST.get('text')
        next_page_id = request.POST.get('next_page_id')
        next_page = find_page(story, next_page_id)
        if not next_page:
            raise PermissionDenied

        data = {
            'text': text,
            'next_page_id': next_page_id
        }

        create_choice(page_id, data)
        return redirect('edit_story', story_id=story_id)

    pages = story.get('pages', [])

    return render(request, 'gameplay/choice_form.html', {
        'story_id': story_id,
        'page_id': page_id,
        'pages': pages
    })


@login_required
def edit_page_view(request, story_id, page_id):
    """View to edit an existing page."""
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    story = get_story_with_pages(story_id)
    if not story:
        return redirect('story_list')
    page = find_page(story, page_id)
    
    if not page:
        raise PermissionDenied

    if request.method == 'POST':
        text = request.POST.get('text')
        is_ending = request.POST.get('is_ending') == 'on'
        ending_label = request.POST.get('ending_label')

        data = {
            'text': text,
            'is_ending': is_ending,
            'ending_label': ending_label if is_ending else None
        }

        update_page(page_id, data)
        return redirect('edit_story', story_id=story_id)

    return render(request, 'gameplay/page_form.html', {
        'story_id': story_id,
        'page': page,
        'action': 'Edit'
    })


@login_required
def delete_page_view(request, story_id, page_id):
    """View to delete a page."""
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    story = get_story_with_pages(story_id)
    if not story:
        return redirect('story_list')
    page = find_page(story, page_id)
    if not page:
        raise PermissionDenied

    if request.method == 'POST':
        delete_page(page_id)
    return redirect('edit_story', story_id=story_id)


@login_required
def edit_choice_view(request, story_id, page_id, choice_id):
    """View to edit an existing choice."""
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    story = get_story_with_pages(story_id)
    if not story:
        return redirect('story_list')
    page = find_page(story, page_id)
    if not page:
        raise PermissionDenied
    choice = next((c for c in page.get('choices', []) if str(c.get('id')) == str(choice_id)), None)

    if not choice:
        raise PermissionDenied

    if request.method == 'POST':
        text = request.POST.get('text')
        next_page_id = request.POST.get('next_page_id')
        next_page = find_page(story, next_page_id)
        if not next_page:
            raise PermissionDenied

        data = {
            'text': text,
            'next_page_id': next_page_id
        }

        update_choice(choice_id, data)
        return redirect('edit_story', story_id=story_id)

    pages = story.get('pages', [])
    return render(request, 'gameplay/choice_form.html', {
        'story_id': story_id,
        'page_id': page_id,
        'choice': choice,
        'pages': pages,
        'action': 'Edit'
    })


@login_required
def delete_choice_view(request, story_id, choice_id):
    """View to delete a choice."""
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    story = get_story_with_pages(story_id)
    if not story:
        return redirect('story_list')
    _page, choice = find_choice(story, choice_id)
    if not choice:
        raise PermissionDenied

    if request.method == 'POST':
        delete_choice(choice_id)
    return redirect('edit_story', story_id=story_id)
