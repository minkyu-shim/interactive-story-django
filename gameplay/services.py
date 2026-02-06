import requests

# Update this to your deployed URL if needed
FLASK_URL = "https://interactive-story-api-dylv.onrender.com"

def get_stories():
    """Fetches list of stories."""
    try:
        response = requests.get(f"{FLASK_URL}/api/stories")
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return []

def get_story_start(story_id):
    """Fetches the start node of a story."""
    try:
        response = requests.get(f"{FLASK_URL}/api/stories/{story_id}/start")
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None

def get_node(story_id, node_id):
    """
    Fetches a specific node using the story_id and custom_id (string).
    URL matches Flask: /stories/<id>/nodes/<custom_id>
    """
    try:
        # Note: node_id is now a string (e.g., 'node_01'), not an int
        response = requests.get(f"{FLASK_URL}/api/stories/{story_id}/nodes/{node_id}")
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None