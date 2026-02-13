import requests

# Update this to your deployed URL if needed
FLASK_URL = "https://interactive-story-api-dylv.onrender.com"


def get_stories(params=None):
    """Fetches list of stories with optional filters."""
    try:
        response = requests.get(f"{FLASK_URL}/api/stories", params=params)
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


def create_story(data):
    """Creates a new story."""

    try:

        response = requests.post(f"{FLASK_URL}/api/stories", json=data)

        if response.status_code == 201:
            return response.json()

    except requests.RequestException:

        return None

    return None


def update_story(story_id, data):
    """Updates an existing story."""

    try:

        response = requests.put(f"{FLASK_URL}/api/stories/{story_id}", json=data)

        if response.status_code == 200:
            return response.json()

    except requests.RequestException:

        return None

    return None


def delete_story(story_id):
    """Deletes a story."""

    try:

        response = requests.delete(f"{FLASK_URL}/api/stories/{story_id}")

        return response.status_code == 204 or response.status_code == 200

    except requests.RequestException:

        return False


def create_page(story_id, data):
    """Creates a new page (node) for a story."""

    try:

        response = requests.post(f"{FLASK_URL}/api/stories/{story_id}/pages", json=data)

        if response.status_code == 201:
            return response.json()

    except requests.RequestException:

        return None

    return None


def create_choice(page_id, data):
    """Creates a new choice for a page."""

    try:

        # Note: The prompt says /pages/<id>/choices

        response = requests.post(f"{FLASK_URL}/api/pages/{page_id}/choices", json=data)

        if response.status_code == 201:
            return response.json()

    except requests.RequestException:

        return None

    return None


def get_story_details(story_id):
    """Fetches full details of a story."""

    try:

        response = requests.get(f"{FLASK_URL}/api/stories/{story_id}")

        if response.status_code == 200:
            return response.json()

    except requests.RequestException:

        return None

    return None
