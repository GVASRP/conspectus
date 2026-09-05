#!/bin/bash
set -euo pipefail

APP=/opt/conspectus
cd "$APP"

log() { echo "[install] $*"; }

log "checking python venv + build deps + git"
NEED=
command -v git >/dev/null 2>&1 || NEED="$NEED git"
if ! python3 -m venv --help >/dev/null 2>&1; then NEED="$NEED python3-venv"; fi
if [ -n "$NEED" ]; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y $NEED
fi
if [ ! -f /usr/include/python3*/Python.h ]; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3-dev build-essential
fi

log "removing caches"
find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

log "creating venv"
python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip wheel setuptools

log "installing deps"
.venv/bin/pip install --quiet -r requirements.txt

log "installing systemd units"
rm -f /etc/systemd/system/conspectus-*.service
cp deploy/conspectus-web.service /etc/systemd/system/
cp deploy/conspectus-bot.service /etc/systemd/system/
cp deploy/conspectus-update.service /etc/systemd/system/
cp deploy/conspectus-update.timer /etc/systemd/system/
systemctl daemon-reload

log "starting services"
systemctl enable --now conspectus-web
systemctl enable --now conspectus-bot
systemctl enable --now conspectus-update.timer
systemctl --no-pager status conspectus-web conspectus-bot | head -n 40

log "done"