#!/usr/bin/env bash
set -euo pipefail

APP_MODULE=${APP_MODULE:-"app:create_app()"}
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"5000"}
WORKERS=${WORKERS:-"4"}
THREADS=${THREADS:-"4"}
TIMEOUT=${TIMEOUT:-"30"}
CERT_FILE=${CERT_FILE:-"cert.pem"}
KEY_FILE=${KEY_FILE:-"key.pem"}

if ! command -v gunicorn >/dev/null 2>&1; then
  echo "gunicorn not found. Install with: pip install gunicorn" >&2
  exit 1
fi

bind="${HOST}:${PORT}"

tls_args=()
if [[ -f "$CERT_FILE" && -f "$KEY_FILE" ]]; then
  tls_args+=(--certfile "$CERT_FILE" --keyfile "$KEY_FILE")
fi

exec gunicorn \
  -w "$WORKERS" \
  -k gthread \
  --threads "$THREADS" \
  --timeout "$TIMEOUT" \
  -b "$bind" \
  "${tls_args[@]}" \
  "$APP_MODULE"
