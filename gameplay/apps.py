from django.apps import AppConfig
import threading
import requests

FLASK_URL = "https://interactive-story-api-dylv.onrender.com"

def wake_up_flask():
    """Sends a request to Flask to wake it up from sleep."""
    try:
        print(f"Pinging Flask at {FLASK_URL} to wake it up...")
        # We use a short timeout so Django doesn't freeze waiting for it
        requests.get(f"{FLASK_URL}/stories", timeout=1)
    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
        # This is expected! The first request often times out while waking up.
        # But the signal has been sent, so Render is starting the server.
        print("Wake-up signal sent! Flask should be ready in ~30 seconds.")

class GameplayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gameplay'

    def ready(self):
        # We run this in a separate thread so it doesn't block Django from starting
        threading.Thread(target=wake_up_flask).start()