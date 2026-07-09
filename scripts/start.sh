#!/bin/sh
set -eu

mkdir -p "${DATA_DIR:-/tmp/website-data}"

echo "Starting FastAPI on 127.0.0.1:8081"
cd /app/backend
PYTHONPATH=/app/backend python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8081 --log-level info &
API_PID=$!

# Wait until API responds (or fail after ~45s)
i=0
while [ "$i" -lt 45 ]; do
  if curl -fsS "http://127.0.0.1:8081/healthz" >/dev/null 2>&1; then
    echo "API is ready"
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "API process exited early" >&2
    wait "$API_PID" || true
    exit 1
  fi
  i=$((i + 1))
  sleep 1
done

if [ "$i" -ge 45 ]; then
  echo "API failed to become ready" >&2
  kill "$API_PID" 2>/dev/null || true
  exit 1
fi

rm -f /etc/nginx/sites-enabled/default

echo "Starting nginx on :8080"
nginx -g 'daemon off;' &
NGINX_PID=$!

term() {
  echo "Shutting down"
  kill "$API_PID" "$NGINX_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
  wait "$NGINX_PID" 2>/dev/null || true
}
trap term INT TERM

while kill -0 "$API_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
  sleep 2
done

echo "A process exited; shutting down" >&2
term
exit 1
