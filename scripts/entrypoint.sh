#!/usr/bin/env sh
set -e

# Production entrypoint:
# - waits for DB
# - runs migrate
# - collects static into STATIC_ROOT (defaults to /static in production compose)
# - starts gunicorn

echo "[entrypoint] starting..."

if [ -n "$POSTGRES_HOST" ]; then
  echo "[entrypoint] waiting for postgres at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}"
  python - <<'PY'
import os, socket, time
host = os.getenv('POSTGRES_HOST','db')
port = int(os.getenv('POSTGRES_PORT','5432'))
for i in range(60):
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        print("[entrypoint] postgres is up")
        break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("[entrypoint] postgres not reachable after 60s")
PY
fi

echo "[entrypoint] running migrations"
python manage.py migrate --noinput

echo "[entrypoint] collecting static"
python manage.py collectstatic --noinput

echo "[entrypoint] launching gunicorn"
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers ${GUNICORN_WORKERS:-3} \
  --timeout ${GUNICORN_TIMEOUT:-60} \
  --access-logfile - \
  --error-logfile -
