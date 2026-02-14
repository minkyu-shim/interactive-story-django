from django.apps import AppConfig
from django.conf import settings
import logging
import os
import sys
import threading
import requests

logger = logging.getLogger(__name__)
FLASK_URL = getattr(settings, "FLASK_BASE_URL", "https://interactive-story-api-dylv.onrender.com")
REQUEST_TIMEOUT = getattr(settings, "FLASK_REQUEST_TIMEOUT", 10)
SKIP_COMMANDS = {
    "check",
    "collectstatic",
    "createsuperuser",
    "dbshell",
    "makemigrations",
    "migrate",
    "shell",
    "showmigrations",
    "test",
}


def should_wake_up_flask():
    if not getattr(settings, "WAKE_UP_FLASK_ON_STARTUP", True):
        return False
    if len(sys.argv) > 1 and sys.argv[1] in SKIP_COMMANDS:
        return False
    if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
        return False
    return True

def wake_up_flask():
    """Sends a request to Flask to wake it up from sleep."""
    try:
        logger.info("Pinging Flask at %s to wake it up...", FLASK_URL)
        requests.get(f"{FLASK_URL}/api/stories", timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        logger.info("Wake-up signal sent. Flask should be ready shortly.")

class GameplayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gameplay'

    def ready(self):
        if should_wake_up_flask():
            # Run wake-up asynchronously so startup isn't blocked by the network call.
            threading.Thread(target=wake_up_flask, daemon=True).start()
