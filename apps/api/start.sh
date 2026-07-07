#!/bin/sh
set -eu

if [ "${START_LOCAL_REDIS:-false}" = "true" ]; then
  redis-server --save "" --appendonly no --daemonize yes
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
