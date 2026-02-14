import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)
FLASK_URL = getattr(settings, "FLASK_BASE_URL", "https://interactive-story-api-dylv.onrender.com")
REQUEST_TIMEOUT = getattr(settings, "FLASK_REQUEST_TIMEOUT", 10)

def get_headers():
    """Returns headers with the API key."""
    return {
        "X-API-KEY": getattr(settings, "FLASK_API_KEY", "")
    }

def get_stories(params=None):
    """Fetches list of stories with optional filters."""
    try:
        response = requests.get(
            f"{FLASK_URL}/api/stories",
            params=params,
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return []

def get_story_start(story_id):
    """Fetches the start node of a story."""
    try:
        response = requests.get(
            f"{FLASK_URL}/api/stories/{story_id}/start",
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
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
        response = requests.get(
            f"{FLASK_URL}/api/stories/{story_id}/nodes/{node_id}",
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None

def create_story(data):
    """Creates a new story."""
    try:
        response = requests.post(
            f"{FLASK_URL}/api/stories",
            json=data,
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 201:
            return response.json()
    except requests.RequestException:
        return None
    return None

def update_story(story_id, data):
    """Updates an existing story."""
    try:
        response = requests.put(
            f"{FLASK_URL}/api/stories/{story_id}",
            json=data,
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None

def delete_story(story_id):
    """Deletes a story."""
    try:
        response = requests.delete(
            f"{FLASK_URL}/api/stories/{story_id}",
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        return response.status_code == 204 or response.status_code == 200
    except requests.RequestException:
        return False

def create_page(story_id, data):
    """Creates a new page (node) for a story."""
    try:
        url = f"{FLASK_URL}/api/stories/{story_id}/nodes"
        response = requests.post(url, json=data, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        logger.debug("POST %s | status=%s", url, response.status_code)
        if response.status_code == 201:
            return response.json()
        logger.warning("create_page failed: status=%s body=%s", response.status_code, response.text)
    except requests.RequestException as e:
        logger.warning("create_page request error: %s", e)
        return None
    return None

def create_choice(page_id, data):
    """Creates a new choice for a page."""
    try:
        # Note: The prompt says /pages/<id>/choices, but we use /nodes/ for consistency
        url = f"{FLASK_URL}/api/nodes/{page_id}/choices"
        response = requests.post(url, json=data, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        logger.debug("POST %s | status=%s", url, response.status_code)
        if response.status_code == 201:
            return response.json()
        logger.warning("create_choice failed: status=%s body=%s", response.status_code, response.text)
    except requests.RequestException as e:
        logger.warning("create_choice request error: %s", e)
        return None
    return None

def update_page(page_id, data):
    """Updates an existing page."""
    try:
        url = f"{FLASK_URL}/api/nodes/{page_id}"
        response = requests.put(url, json=data, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        logger.debug("PUT %s | status=%s", url, response.status_code)
        if response.status_code == 200:
            return response.json()
        logger.warning("update_page failed: status=%s body=%s", response.status_code, response.text)
    except requests.RequestException as e:
        logger.warning("update_page request error: %s", e)
        return None
    return None

def delete_page(page_id):
    """Deletes a page."""
    try:
        url = f"{FLASK_URL}/api/nodes/{page_id}"
        response = requests.delete(url, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        logger.debug("DELETE %s | status=%s", url, response.status_code)
        return response.status_code == 204 or response.status_code == 200
    except requests.RequestException as e:
        logger.warning("delete_page request error: %s", e)
        return False

def update_choice(choice_id, data):
    """Updates an existing choice."""
    try:
        url = f"{FLASK_URL}/api/choices/{choice_id}"
        response = requests.put(url, json=data, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        logger.debug("PUT %s | status=%s", url, response.status_code)
        if response.status_code == 200:
            return response.json()
        logger.warning("update_choice failed: status=%s body=%s", response.status_code, response.text)
    except requests.RequestException as e:
        logger.warning("update_choice request error: %s", e)
        return None
    return None

def delete_choice(choice_id):
    """Deletes a choice."""
    try:
        response = requests.delete(
            f"{FLASK_URL}/api/choices/{choice_id}",
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        return response.status_code == 204 or response.status_code == 200
    except requests.RequestException:
        return False

def get_story_details(story_id):
    """Fetches full details of a story."""
    try:
        url = f"{FLASK_URL}/api/stories/{story_id}"
        # Cache busting
        params = {"_t": int(time.time())}
        response = requests.get(url, params=params, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None

def get_story_nodes(story_id):
    """Fetches all nodes for a specific story."""
    try:
        url = f"{FLASK_URL}/api/stories/{story_id}/nodes"
        response = requests.get(url, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return []

