import logging
import random
import re
from copy import deepcopy
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Play, PlaySession, StoryOwnership, StoryRatingComment, StoryReport
from .forms import StoryRatingCommentForm, StoryReportForm, StoryReportModerationForm
from .services import (
    get_stories, get_story_start, get_node, get_story_details,
    create_story, update_story, delete_story, create_page, create_choice,
    update_page, delete_page, update_choice, delete_choice, get_story_nodes
)
from django.db.models import Count, Avg, Q

logger = logging.getLogger(__name__)
VALID_STORY_STATUSES = {'draft', 'published', 'suspended'}
PLAYER_NAME_SESSION_KEY = 'story_player_names'
PLAYER_NAME_PLACEHOLDERS = (
    '{{player_name}}',
    '{player_name}',
    '[[player_name]]',
    '<player_name>',
)
PLAYER_SPEAKER_ALIASES = {'user', 'jin', '진'}


def _current_story_source():
    return (getattr(settings, 'FLASK_BASE_URL', '') or '').rstrip('/')


def _default_player_name(request):
    return 'user'


def _normalize_player_name(raw_name, fallback='user'):
    normalized = re.sub(r'\s+', ' ', (raw_name or '').strip())
    if not normalized:
        return fallback
    normalized = ''.join(ch for ch in normalized if ch.isalnum() or ch in " _-'.")
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    if not normalized:
        return fallback
    return normalized[:30].strip() or fallback


def _story_name_map(request):
    names = request.session.get(PLAYER_NAME_SESSION_KEY, {})
    return names if isinstance(names, dict) else {}


def _player_name_for_story(request, story_id):
    names = _story_name_map(request)
    default_name = _default_player_name(request)
    return names.get(str(story_id)) or default_name


def _set_player_name_for_story(request, story_id, player_name):
    names = _story_name_map(request)
    names[str(story_id)] = player_name
    request.session[PLAYER_NAME_SESSION_KEY] = names
    request.session.modified = True


def _replace_player_name_tokens(value, player_name):
    if not isinstance(value, str):
        return value
    replaced = value
    for placeholder in PLAYER_NAME_PLACEHOLDERS:
        replaced = replaced.replace(placeholder, player_name)
    return replaced


def _speaker_is_player_alias(value):
    if not isinstance(value, str):
        return False
    speaker = value.strip()
    if not speaker:
        return False
    return speaker.casefold() in PLAYER_SPEAKER_ALIASES


def _inject_player_name(node_data, player_name):
    rendered = deepcopy(node_data)

    for text_key in ('title', 'text', 'ending_label', 'outcome'):
        rendered[text_key] = _replace_player_name_tokens(rendered.get(text_key), player_name)

    for list_key in ('dialogue', 'content'):
        lines = rendered.get(list_key)
        if not isinstance(lines, list):
            continue
        updated_lines = []
        for line in lines:
            if not isinstance(line, dict):
                updated_lines.append(line)
                continue
            updated = dict(line)
            updated_speaker = updated.get('speaker')
            if _speaker_is_player_alias(updated_speaker):
                updated['speaker'] = player_name
            else:
                updated['speaker'] = _replace_player_name_tokens(updated_speaker, player_name)
            updated['text'] = _replace_player_name_tokens(updated.get('text'), player_name)
            updated_lines.append(updated)
        rendered[list_key] = updated_lines

    choices = rendered.get('choices')
    if isinstance(choices, list):
        updated_choices = []
        for choice in choices:
            if not isinstance(choice, dict):
                updated_choices.append(choice)
                continue
            updated = dict(choice)
            updated['text'] = _replace_player_name_tokens(updated.get('text'), player_name)
            updated['label'] = _replace_player_name_tokens(updated.get('label'), player_name)
            updated['effect'] = _replace_player_name_tokens(updated.get('effect'), player_name)
            updated_choices.append(updated)
        rendered['choices'] = updated_choices

    return rendered


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
    source = _current_story_source()
    rating_stats = StoryRatingComment.objects.filter(story_source=source).values('story_id').annotate(
        avg_rating=Avg('rating'),
        count=Count('id'),
    )
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
    source = _current_story_source()
    rating_stats = StoryRatingComment.objects.filter(story_source=source).values('story_id').annotate(
        avg_rating=Avg('rating'),
        count=Count('id'),
    )
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

    if request.method == 'POST':
        fallback_name = _player_name_for_story(request, story_id)
        chosen_name = _normalize_player_name(request.POST.get('player_name'), fallback=fallback_name)
        _set_player_name_for_story(request, story_id, chosen_name)
        PlaySession.objects.filter(session_key=request.session.session_key, story_id=story_id).delete()

        start_node = get_story_start(story_id)
        if start_node:
            return redirect('play_node', story_id=story_id, node_id=start_node['id'])
        return redirect('story_list')

    story = get_story_details(story_id) or {}
    return render(request, 'gameplay/start_story.html', {
        'story_id': story_id,
        'story_title': story.get('title', f'Story #{story_id}'),
        'initial_player_name': _player_name_for_story(request, story_id),
    })


def play_node(request, story_id, node_id):
    node_data = get_node(story_id, node_id)

    if not node_data:
        return redirect('story_list')
    player_name = _player_name_for_story(request, story_id)
    node_data = _inject_player_name(node_data, player_name)

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

    source = _current_story_source()
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
        ratings_comments = StoryRatingComment.objects.filter(
            story_source=source,
            story_id=story_id,
        ).order_by('-created_at')
        if request.user.is_authenticated:
            existing_rating = StoryRatingComment.objects.filter(
                user=request.user,
                story_source=source,
                story_id=story_id,
            ).first()
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
        'player_name': player_name,
        'is_ending': is_actually_ending,
        'is_preview': is_preview,
        'ratings_comments': ratings_comments,
        'user_rating_form': user_rating_form
    })


def choose_choice(request, story_id, node_id):
    if request.method != 'POST':
        return redirect('play_node', story_id=story_id, node_id=node_id)

    node_data = get_node(story_id, node_id)
    if not node_data:
        return redirect('story_list')

    choice_id = request.POST.get('choice_id')
    selected_choice = _find_choice_in_node(node_data, choice_id)
    if not selected_choice:
        messages.error(request, 'Selected choice is no longer available.')
        return redirect('play_node', story_id=story_id, node_id=node_id)

    primary_target = _choice_target(selected_choice)
    if not primary_target:
        messages.error(request, 'This choice has no valid destination.')
        return redirect('play_node', story_id=story_id, node_id=node_id)

    if selected_choice.get('requires_roll'):
        roll_sides = _as_int(selected_choice.get('roll_sides'), 6)
        roll_sides = min(max(roll_sides, 2), 100)
        roll_required = _as_int(selected_choice.get('roll_required'), max(1, (roll_sides + 1) // 2))
        roll_required = min(max(roll_required, 1), roll_sides)
        rolled = random.randint(1, roll_sides)

        if rolled >= roll_required:
            messages.success(request, f"Dice roll {rolled}/{roll_sides} succeeded (needed {roll_required}+).")
            next_node_id = primary_target
        else:
            fail_target = selected_choice.get('on_fail_target')
            if fail_target:
                messages.warning(
                    request,
                    f"Dice roll {rolled}/{roll_sides} failed (needed {roll_required}+). You were redirected.",
                )
                next_node_id = fail_target
            else:
                messages.warning(
                    request,
                    f"Dice roll {rolled}/{roll_sides} failed (needed {roll_required}+). Choice is inaccessible.",
                )
                next_node_id = node_id
    else:
        next_node_id = primary_target

    return redirect('play_node', story_id=story_id, node_id=str(next_node_id))


@login_required
def submit_rating_comment(request, story_id):
    source = _current_story_source()
    if request.method == 'POST':
        existing_rating = StoryRatingComment.objects.filter(
            user=request.user,
            story_source=source,
            story_id=story_id,
        ).first()
        if existing_rating:
            form = StoryRatingCommentForm(request.POST, instance=existing_rating)
        else:
            form = StoryRatingCommentForm(request.POST)

        if form.is_valid():
            rating_comment = form.save(commit=False)
            rating_comment.user = request.user
            rating_comment.story_id = story_id
            rating_comment.story_source = source
            rating_comment.save()

    return redirect(request.META.get('HTTP_REFERER', 'story_list'))


@login_required
def submit_story_report(request, story_id):
    story = get_story_details(story_id) or {}
    story_title = story.get('title', '') if isinstance(story, dict) else ''
    existing_report = StoryReport.objects.filter(user=request.user, story_id=story_id).first()

    if request.method == 'POST':
        form = StoryReportForm(request.POST, instance=existing_report)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.story_id = story_id
            if story_title:
                report.story_title_snapshot = story_title
            report.status = StoryReport.Status.OPEN
            report.resolved_by = None
            report.resolved_at = None
            report.save()
            messages.success(request, 'Report submitted. Our admin team will review it.')
            return redirect('story_list')
    else:
        form = StoryReportForm(instance=existing_report)

    return render(request, 'gameplay/story_report_form.html', {
        'form': form,
        'story_id': story_id,
        'story_title': story_title or f"Story #{story_id}",
        'existing_report': existing_report,
    })


@login_required
def report_moderation_list(request):
    if not request.user.is_staff:
        raise PermissionDenied

    status_filter = request.GET.get('status', '')
    reason_filter = request.GET.get('reason', '')
    query = request.GET.get('q', '').strip()

    reports = StoryReport.objects.select_related('user', 'resolved_by').order_by('-created_at')

    if status_filter:
        reports = reports.filter(status=status_filter)
    if reason_filter:
        reports = reports.filter(reason=reason_filter)
    if query:
        query_filter = (
            Q(story_title_snapshot__icontains=query) |
            Q(details__icontains=query) |
            Q(admin_note__icontains=query) |
            Q(user__username__icontains=query)
        )
        if query.isdigit():
            query_filter |= Q(story_id=int(query))
        reports = reports.filter(query_filter)

    report_rows = [
        {
            'report': report,
            'form': StoryReportModerationForm(instance=report, prefix=f"r{report.id}"),
        }
        for report in reports
    ]

    return render(request, 'gameplay/report_moderation_list.html', {
        'report_rows': report_rows,
        'status_filter': status_filter,
        'reason_filter': reason_filter,
        'query': query,
        'status_choices': StoryReport.Status.choices,
        'reason_choices': StoryReport.Reason.choices,
    })


@login_required
def report_moderation_update(request, report_id):
    if not request.user.is_staff:
        raise PermissionDenied

    if request.method != 'POST':
        return redirect('moderation_reports')

    report = get_object_or_404(StoryReport, id=report_id)
    form = StoryReportModerationForm(request.POST, instance=report, prefix=f"r{report.id}")
    redirect_status = None

    if form.is_valid():
        updated_report = form.save(commit=False)
        if updated_report.status in {StoryReport.Status.RESOLVED, StoryReport.Status.REJECTED}:
            updated_report.resolved_by = request.user
            updated_report.resolved_at = timezone.now()
        else:
            updated_report.resolved_by = None
            updated_report.resolved_at = None
        updated_report.save()
        redirect_status = updated_report.status
        messages.success(request, f"Report #{report.id} updated.")
    else:
        messages.error(request, f"Invalid update for report #{report.id}.")

    next_url = request.POST.get('next', '')
    if next_url.startswith('/'):
        # Keep the updated row visible after save when a status filter was active.
        parsed = urlsplit(next_url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if redirect_status and params.get('status') and params.get('status') != redirect_status:
            params['status'] = redirect_status
            next_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), parsed.fragment))
        return redirect(next_url)
    return redirect('moderation_reports')


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


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_choice_roll_data(post_data, story):
    requires_roll = post_data.get('requires_roll') == 'on'
    if not requires_roll:
        return {
            'requires_roll': False,
            'roll_sides': None,
            'roll_required': None,
            'on_fail_target': None,
        }

    roll_sides = _as_int(post_data.get('roll_sides'), 6)
    roll_sides = min(max(roll_sides, 2), 100)
    roll_required = _as_int(post_data.get('roll_required'), max(1, (roll_sides + 1) // 2))
    roll_required = min(max(roll_required, 1), roll_sides)

    on_fail_target = post_data.get('on_fail_target') or None
    if on_fail_target and not find_page(story, on_fail_target):
        raise PermissionDenied

    return {
        'requires_roll': True,
        'roll_sides': roll_sides,
        'roll_required': roll_required,
        'on_fail_target': on_fail_target,
    }


def _find_choice_in_node(node_data, choice_id):
    return next((c for c in node_data.get('choices', []) if str(c.get('id')) == str(choice_id)), None)


def _choice_target(choice):
    return (
        choice.get('next_page_id')
        or choice.get('target_node')
        or choice.get('target')
    )


def _story_graph_payload(story):
    pages = story.get('pages', []) or []
    node_ids = []
    page_map = {}

    for page in pages:
        page_id = page.get('id')
        if page_id is None:
            continue
        page_id = str(page_id)
        node_ids.append(page_id)
        page_map[page_id] = page

    start_node_id = story.get('start_node_id')
    if start_node_id is not None:
        start_node_id = str(start_node_id)
    elif node_ids:
        start_node_id = node_ids[0]

    adjacency = {node_id: [] for node_id in node_ids}
    missing_nodes = set()
    graph_edges = []

    for page in pages:
        source_id = page.get('id')
        if source_id is None:
            continue
        source_id = str(source_id)
        for index, choice in enumerate(page.get('choices', []) or []):
            target_raw = _choice_target(choice)
            if target_raw is None:
                continue
            target_id = str(target_raw)
            is_broken = target_id not in adjacency
            render_target = target_id
            if is_broken:
                render_target = f"missing::{target_id}"
                missing_nodes.add(target_id)
            else:
                adjacency[source_id].append(target_id)

            choice_label = (choice.get('text') or choice.get('label') or '').strip()
            if len(choice_label) > 56:
                choice_label = f"{choice_label[:53]}..."

            edge_id_source = choice.get('id', index)
            graph_edges.append({
                'data': {
                    'id': f"edge::{source_id}::{render_target}::{edge_id_source}",
                    'source': source_id,
                    'target': render_target,
                    'label': choice_label,
                    'broken_target': target_id if is_broken else '',
                },
                'classes': 'broken' if is_broken else '',
            })

    reachable = set()
    if start_node_id in adjacency:
        stack = [start_node_id]
        while stack:
            current = stack.pop()
            if current in reachable:
                continue
            reachable.add(current)
            stack.extend(adjacency.get(current, []))

    unreachable = [node_id for node_id in node_ids if node_id not in reachable]

    graph_nodes = []
    for node_id in node_ids:
        page = page_map[node_id]
        title = page.get('title') or f"Node {node_id}"
        short_title = title if len(title) <= 42 else f"{title[:39]}..."
        node_label = f"{node_id}\n{short_title}"
        node_classes = []
        if node_id == start_node_id:
            node_classes.append('start')
        if page.get('is_ending') or page.get('type') == 'ending':
            node_classes.append('ending')
        if node_id in unreachable:
            node_classes.append('unreachable')

        graph_nodes.append({
            'data': {
                'id': node_id,
                'label': node_label,
                'full_title': title,
                'text_preview': (page.get('text') or '')[:280],
            },
            'classes': ' '.join(node_classes),
        })

    for missing_target_id in sorted(missing_nodes):
        graph_nodes.append({
            'data': {
                'id': f"missing::{missing_target_id}",
                'label': f"Missing: {missing_target_id}",
                'full_title': 'Missing target node',
                'text_preview': '',
            },
            'classes': 'missing',
        })

    graph_elements = graph_nodes + graph_edges

    broken_edge_count = sum(1 for edge in graph_edges if edge.get('classes') == 'broken')

    return {
        'graph_elements': graph_elements,
        'start_node_id': start_node_id or '',
        'node_count': len(node_ids),
        'edge_count': len(graph_edges),
        'unreachable_count': len(unreachable),
        'broken_edge_count': broken_edge_count,
        'unreachable_node_ids': unreachable,
    }


@login_required
def story_graph_view(request, story_id):
    if not check_ownership(request.user, story_id):
        raise PermissionDenied

    story = get_story_with_pages(story_id)
    if not story:
        return redirect('story_list')

    graph_payload = _story_graph_payload(story)
    return render(request, 'gameplay/story_graph.html', {
        'story': story,
        'story_id': story_id,
        **graph_payload,
    })


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
        illustration_url = (request.POST.get('illustration_url') or '').strip() or None

        import uuid
        data = {
            'title': f"Node {uuid.uuid4().hex[:6]}",  # Add a title
            'custom_id': f"node_{uuid.uuid4().hex[:8]}", # Add a custom_id
            'text': text,
            'is_ending': is_ending,
            'ending_label': ending_label if is_ending else None,
            'illustration_url': illustration_url,
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
        roll_data = _extract_choice_roll_data(request.POST, story)

        data = {
            'text': text,
            'next_page_id': next_page_id,
            **roll_data,
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
        illustration_url = (request.POST.get('illustration_url') or '').strip() or None

        data = {
            'text': text,
            'is_ending': is_ending,
            'ending_label': ending_label if is_ending else None,
            'illustration_url': illustration_url,
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
        roll_data = _extract_choice_roll_data(request.POST, story)

        data = {
            'text': text,
            'next_page_id': next_page_id,
            **roll_data,
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
