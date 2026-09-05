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
  log "provisioning: web on port 80"
  grep -q '^WEB_PORT=80' .env 2>/dev/null || echo 'WEB_PORT=80' >> .env
  grep -q '^PUBLIC_URL=http://138.16.191.99$' .env 2>/dev/null || echo 'PUBLIC_URL=http://138.16.191.99' >> .env
  for s in nginx apache2 httpd caddy; do
    if systemctl is-active --quiet "$s" 2>/dev/null; then
      systemctl stop "$s" || true
      systemctl disable "$s" 2>/dev/null || true
      log "stopped $s"
    fi
  done
  touch "$FLAG"
fi

OLD_HTTP_PIDS=$(ss -tlnp 2>/dev/null | grep -E ':(80|443) ' | sed -E 's/.*pid=([0-9]+)/\1/' | cut -d, -f1 | sort -u)
for pid in $OLD_HTTP_PIDS; do
  kill -9 "$pid" 2>/dev/null || true
done

.venv/bin/pip install -q -r requirements.txt || true

systemctl restart conspectus-web conspectus-bot || true
log "ok $(git rev-parse --short HEAD)"