#!/bin/bash
set -euo pipefail
cd /opt/conspectus
export GIT_TERMINAL_PROMPT=0
OLD=$(git rev-parse HEAD)
if git pull --ff-only -q; then
  if [ "$OLD" != "$(git rev-parse HEAD)" ]; then
    .venv/bin/pip install -q -r requirements.txt || true
    systemctl restart conspectus-web conspectus-bot || true
    echo "[update] applied $(git rev-parse --short HEAD)"
  else
    echo "[update] up to date"
  fi
else
  echo "[update] pull failed; retry later"
  exit 1
fi