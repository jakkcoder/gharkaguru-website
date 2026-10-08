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

# /demo -> internal demo app (cluster service; not reachable from outside).
# nginx resolves the name per request, so the site still starts if the demo
# service is down. The demo admin (/demo/admin) is behind its own password.
mkdir -p /etc/nginx/demo-proxy
rm -f /etc/nginx/demo-proxy/demo.conf
if [ -n "${DEMO_APP_URL:-}" ]; then
  DNS="${DEMO_DNS_RESOLVER:-$(awk '/^nameserver/ { print $2; exit }' /etc/resolv.conf)}"
  case "$DNS" in *:*) DNS="[$DNS]" ;; esac
  cat > /etc/nginx/demo-proxy/demo.conf <<CONF
location = /demo {
  absolute_redirect off;
  return 301 /demo/;
}

location ^~ /demo/ {
  resolver ${DNS} valid=30s ipv6=off;
  set \$demo_upstream ${DEMO_APP_URL};
  proxy_pass \$demo_upstream;
  proxy_http_version 1.1;
  proxy_set_header Host \$host;
  proxy_set_header X-Real-IP \$remote_addr;
  proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto \$scheme;
  # Recording uploads arrive in 4-second parts; stream them straight through.
  # Fail fast while the demo app restarts; the recorder retries each part.
  proxy_connect_timeout 5s;
  client_max_body_size 60m;
  proxy_request_buffering off;
  proxy_read_timeout 300s;
  proxy_send_timeout 300s;
}
CONF
  echo "Demo app proxied at /demo -> ${DEMO_APP_URL} (resolver ${DNS})"
fi
nginx -t

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
