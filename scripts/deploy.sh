#!/usr/bin/env bash
set -euo pipefail

REMOTE="${DEPLOY_HOST:-}"
REMOTE_PATH="${DEPLOY_PATH:-/opt/outfit-ai}"

if [[ -z "$REMOTE" ]]; then
  echo "用法：DEPLOY_HOST=ubuntu@服务器公网IP ./scripts/deploy.sh" >&2
  exit 2
fi

command -v ssh >/dev/null || { echo "本机缺少 ssh" >&2; exit 1; }
command -v rsync >/dev/null || { echo "本机缺少 rsync" >&2; exit 1; }

ssh "$REMOTE" "mkdir -p '$REMOTE_PATH'"

rsync -az \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'data/' \
  --exclude 'backend/data/' \
  --exclude 'frontend/node_modules/' \
  --exclude 'node_modules/' \
  --exclude '.playwright-cli/' \
  --exclude 'images/' \
  --exclude 'output/' \
  ./ "$REMOTE:$REMOTE_PATH/"

if ! ssh "$REMOTE" "test -f '$REMOTE_PATH/.env.production'"; then
  echo "服务器缺少 $REMOTE_PATH/.env.production；请先复制 .env.production.example 并填写密钥。" >&2
  exit 1
fi

ssh "$REMOTE" "cd '$REMOTE_PATH' && sudo env OUTFIT_AI_DEPLOY_PATH='$REMOTE_PATH' bash deploy/install-scheduler.sh"
ssh "$REMOTE" "cd '$REMOTE_PATH' && docker compose --env-file .env.production up -d --build --remove-orphans"
ssh "$REMOTE" "cd '$REMOTE_PATH' && docker compose ps"
ssh "$REMOTE" "cd '$REMOTE_PATH' && docker compose exec -T app python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)\""

echo "部署完成：$REMOTE_PATH"
