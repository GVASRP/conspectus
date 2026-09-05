#!/bin/bash
set -uo pipefail
cd /opt/conspectus
export GIT_TERMINAL_PROMPT=0

log() { echo "[update] $*"; }

OLD=$(git rev-parse HEAD)
if ! git pull --ff-only -q; then
  log "pull failed, continuing"
fi

FLAG=/opt/conspectus/.www-on-80
if [ ! -f "$FLAG" ]; then
  log "enabling web on port 80"
  grep -q '^WEB_PORT=80' .env 2>/dev/null || echo 'WEB_PORT=80' >> .env
  grep -q '^PUBLIC_URL=http://138.16.191.99$' .env 2>/dev/null || echo 'PUBLIC_URL=http://138.16.191.99' >> .env
  if systemctl is-active --quiet nginx 2>/dev/null; then
    systemctl stop nginx || true
    systemctl disable nginx || true
    log "stopped old nginx"
  fi
  touch "$FLAG"
fi

NEW=$(git rev-parse HEAD)
if [ "$OLD" != "$NEW" ] || [ "$(cat "$FLAG" 2>/dev/null)" = "" ]; then
  :
fi

.venv/bin/pip install -q -r requirements.txt || true

systemctl restart conspectus-web conspectus-bot || true
log "ok $(git rev-parse --short HEAD)"