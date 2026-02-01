import requests

# This is the address of Flask app for now
FLASK_URL = "http://127.0.0.1:5000"

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