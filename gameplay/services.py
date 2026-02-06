import requests

# This is the address of Flask app for now
FLASK_URL = "https://interactive-story-api-dylv.onrender.com"

def get_stories():
    """Fetches all published stories from the Flask API."""
    try:
        # Asks Flask for only the published stories
        response = requests.get(f"{FLASK_URL}/stories?status=published")
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.ConnectionError:
        print("Error: Flask server is not running!")
    return []

def get_page(page_id):
    """Fetches a specific page and its choices from Flask."""
    response = requests.get(f"{FLASK_URL}/pages/{page_id}")
    return response.json() if response.status_code == 200 else None

def get_story_start(story_id):
    """Fetches the first page of a story from Flask."""
    try:
        response = requests.get(f"{FLASK_URL}/stories/{story_id}/start")
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.ConnectionError:
        print("Error: Flask server is not running!")
    return None