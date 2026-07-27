#!/usr/bin/env bash
# exit on error
set -o errexit

if [ -d "backend" ]; then
  cd backend
fi

pip install -r requirements.txt

# During Render's build phase, internal database hostnames (dpg-xxx-a)
# cannot be resolved because the build container is outside the private network.
# Temporarily unset DATABASE_URL so Django falls back to SQLite for collectstatic.
# Real migrations run on startup via the startCommand where DNS resolves correctly.
DATABASE_URL="" python manage.py collectstatic --no-input
