#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请以 root 运行：sudo bash deploy/install-scheduler.sh" >&2
  exit 1
fi

APP_DIR="${OUTFIT_AI_DEPLOY_PATH:-/opt/outfit-ai}"
RUNNER="/usr/local/sbin/outfit-ai-precompute"
CRON_FILE="/etc/cron.d/outfit-ai-precompute"

cat > "$RUNNER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd '$APP_DIR'
/usr/bin/docker compose --env-file .env.production run --rm --no-deps app python -m outfit_ai.precompute_daily
EOF
chmod 755 "$RUNNER"

cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CRON_TZ=Asia/Shanghai
30 6 * * * root /usr/bin/flock -n /run/lock/outfit-ai-precompute.lock '$RUNNER' >> /var/log/outfit-ai-precompute.log 2>&1
EOF
chmod 644 "$CRON_FILE"

echo "已安装 Outfit-AI 每日预生成：06:30 Asia/Shanghai"
