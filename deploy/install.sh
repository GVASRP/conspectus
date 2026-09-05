#!/bin/bash
set -euo pipefail

ZIP="${1:-/tmp/conspectus.zip}"
APP=/opt/conspectus
STAGE=/tmp/conspectus-stage

log() { echo "[install] $*"; }

command -v unzip >/dev/null 2>&1 || apt-get install -y unzip >/dev/null

log "unpacking $ZIP"
rm -rf "$STAGE"
mkdir -p "$STAGE"
unzip -q -o "$ZIP" -d "$STAGE"

log "placing app to $APP"
rm -rf /opt/conspectus.old
if [ -d "$APP" ]; then
  mv "$APP" /opt/conspectus.old
fi
mv "$STAGE" "$APP"
cd "$APP"

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
systemctl daemon-reload

log "starting services"
systemctl enable --now conspectus-web
systemctl enable --now conspectus-bot
systemctl --no-pager status conspectus-web conspectus-bot | head -n 40

log "done"