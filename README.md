# NAHB - Not Another Hero's Book

NAHB is an interactive storytelling platform inspired by *Choose Your Own Adventure* books.
Authors build branching stories, and readers play them by making choices that lead to different endings.

This repository contains the Django web app (`django-engine`) for gameplay, UI, user features, and analytics.
It works together with a separate Flask REST API project (https://github.com/minkyu-shim/interactive-story-api.git) that stores story content.

## Live Deployment

- Go to this page and Wait until it loads (Flask):
  - https://interactive-story-api-dylv.onrender.com

- Then open Main app for testing (Django):
  - https://interactive-story-django.onrender.com

## Demo Credentials

Use this admin account for testing:

- Username: `admin`
- Password: `admin123`

Login pages:

- App login: `/accounts/login/`
- Django admin: `/admin/`

For real production use, change this password immediately.

## Project Goals

- Let authors create branching stories with pages and choices.
- Let readers play stories and reach multiple endings.
- Track play statistics and ending distributions.
- Add authentication, ownership, moderation, ratings, and reports.
- Keep story content in Flask and user/gameplay data in Django.

## Architecture

- Flask API (`../flask`):
  - Source of truth for story content.
  - Stores stories, nodes (pages), and choices.
  - Exposes JSON REST endpoints.
- Django app (`django-engine`):
  - Web UI for readers and authors.
  - Handles gameplay flow, sessions, auth, ratings/comments, reporting, moderation views, and statistics.
  - Calls Flask API through `gameplay/services.py`.

Data boundary:

- Story content data lives in Flask DB.
- Gameplay and user data live in Django DB.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Web | Django 6 |
| Content API | Flask 3 |
| DB (Django) | SQLite |
| DB (Flask) | SQLite by default (configurable with `DATABASE_URL`) |
| ORM | Django ORM + SQLAlchemy |
| HTTP integration | `requests` from Django to Flask API |
| Static serving | WhiteNoise |
| Deployment | Render |

## Main Features

- Reader story list with search/filter.
- Story playing with branching choices and ending screens.
- Anonymous or authenticated play tracking.
- Author dashboard with story CRUD and node/choice editing.
- Story graph visualization (nodes, edges, unreachable/broken targets).
- Authentication (signup/login/logout).
- Story ownership checks for author operations.
- Ratings and comments (1-5 stars + text).
- Story reporting workflow with admin moderation page.
- Draft/published/suspended story statuses.

## Data Models

### Flask Content Models

- `Story`
  - `id`, `title`, `description`, `genre`, `author`, `initial_state`, `status`
- `StoryNode`
  - `id`, `story_id`, `custom_id`, `node_type`, `background`, `illustration_url`, `content_data`, `affinity_change`, `is_ending`, `ending_outcome`
- `Choice`
  - `id`, `node_id`, `text`, `target_node_custom_id`, `effect_description`

### Django Gameplay/User Models

- `Play`
  - user link, `story_id`, `ending_node_id`, timestamp
- `PlaySession`
  - anonymous session resume state (`session_key`, `story_id`, `current_node_id`)
- `StoryOwnership`
  - maps story IDs to owning users
- `StoryRatingComment`
  - user rating (1-5) + comment per story/source
- `StoryReport`
  - user report with reason/status/moderation metadata

## Flask API Reference (Current Implementation)

All endpoints are under `/api`.

- `GET /api/stories`
- `POST /api/stories`
- `GET /api/stories/<story_id>`
- `PUT /api/stories/<story_id>`
- `DELETE /api/stories/<story_id>`
- `GET /api/stories/<story_id>/start`
- `GET /api/stories/<story_id>/nodes`
- `POST /api/stories/<story_id>/nodes`
- `GET /api/stories/<story_id>/nodes/<custom_id>`
- `PUT /api/stories/<story_id>/nodes/<custom_id>`
- `DELETE /api/stories/<story_id>/nodes/<custom_id>`
- `GET /api/nodes/<custom_id>`
- `PUT /api/nodes/<custom_id>`
- `DELETE /api/nodes/<custom_id>`
- `POST /api/stories/<story_id>/nodes/<node_custom_id>/choices`
- `POST /api/nodes/<node_custom_id>/choices`
- `GET /api/choices/<choice_id>`
- `PUT /api/choices/<choice_id>`
- `DELETE /api/choices/<choice_id>`
- `POST /api/import`

## Environment Variables

### Django (`django-engine`)

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev fallback | Django secret key |
| `DJANGO_DEBUG` | `False` | Debug mode |
| `DATABASE_URL` | SQLite fallback | Django DB URL (Postgres in Docker/Render) |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hosts |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` | CSRF trusted origins |
| `FLASK_BASE_URL` | `https://interactive-story-api-dylv.onrender.com` | Flask API base URL |
| `FLASK_API_KEY` | `my-super-secret-api-key` | API key sent by Django |
| `FLASK_REQUEST_TIMEOUT` | `10` | Flask API timeout seconds |
| `WAKE_UP_FLASK_ON_STARTUP` | `True` | Startup warm-up behavior |

### Flask (`../flask`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///project.db` | Flask SQLAlchemy DB URL |
| `FLASK_API_KEY` | `my-super-secret-api-key` | API key expected by Flask |
| `SECRET_KEY` | `dev-secret-key` | Flask app secret |

## Running Locally

### Prerequisites

- Python 3.10+ (3.11 recommended)
- `pip`
- Two terminals if running full stack

### Option A - Run Django only (using deployed Flask API)

1. Setup Django environment.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment variables.

```powershell
$env:DJANGO_DEBUG="True"
$env:DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
$env:FLASK_BASE_URL="https://interactive-story-api-dylv.onrender.com"
$env:FLASK_API_KEY="my-super-secret-api-key"
```

3. Run Django.

```powershell
python manage.py migrate
python manage.py runserver
```

4. Open `http://127.0.0.1:8000`.

### Option B - Run full stack locally (Flask + Django)

1. Start Flask in `../flask`.

```powershell
cd ..\flask
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:FLASK_API_KEY="my-super-secret-api-key"
python seed.py
python run.py
```

2. Start Django in `django-engine` (new terminal).

```powershell
cd ..\django-engine
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:DJANGO_DEBUG="True"
$env:DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
$env:FLASK_BASE_URL="http://127.0.0.1:5000"
$env:FLASK_API_KEY="my-super-secret-api-key"
python manage.py migrate
python manage.py runserver
```

3. Open `http://127.0.0.1:8000`.

Important note:

- Running `python seed.py` in Flask recreates tables and reseeds story content.

## Running with Docker

1. Copy the Docker env template.

```powershell
Copy-Item .env.docker.example .env.docker
```

2. Build and start Django + Postgres.

```powershell
docker compose up --build
```

3. Open `http://127.0.0.1:8000`.

Notes:

- On startup, the container runs `migrate` and `collectstatic`.
- If `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD` are set in `.env.docker`, an admin user is created/updated automatically.
- Django uses Postgres in Docker via `DATABASE_URL=postgresql://django:django@db:5432/django_engine`.

Stop and remove containers:

```powershell
docker compose down
```

## Common Workflows

- Reader:
  - Browse stories, start story, choose branches, reach ending, optionally leave rating/report.
- Author:
  - Login, create story, add/edit/delete nodes and choices, preview graph.
- Admin (`is_staff`):
  - Access moderation reports page and update report status.

## Tests and Useful Commands

### Django

```powershell
python manage.py check
python manage.py test
python manage.py createsuperuser
```

### Flask

```powershell
cd ..\flask
python seed.py
```

## Project Structure (High Level)

- `django_engine/` -> Django settings and URL config
- `gameplay/` -> Django app: models, views, templates, services, tests
- `gameplay/static/` -> CSS/static assets
- `../flask/app/` -> Flask API models and routes
- `../flask/seed.py` -> Flask seed data and story content refresh

## Troubleshooting

- CSS 404 on Django:
  - Ensure `STATIC_URL` is `/static/` and restart server.
- Story pages do not load:
  - Verify `FLASK_BASE_URL` and `FLASK_API_KEY` in Django env.
- Unauthorized from Flask API:
  - Ensure Django and Flask use the same `FLASK_API_KEY`.
- No stories available locally:
  - Rerun `python seed.py` in Flask.

## Notes for Evaluators/Users

- The easiest way to test is the deployed Django URL:
  - https://interactive-story-django.onrender.com
- Local setup is documented above for both quick mode and full-stack mode.
