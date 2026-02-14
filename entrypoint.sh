#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]

user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
print("Superuser ensured.")
PY
else
  echo "Skipping superuser bootstrap (set DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD)."
fi

exec "$@"
