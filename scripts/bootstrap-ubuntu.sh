#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请以 root 运行：sudo bash scripts/bootstrap-ubuntu.sh" >&2
  exit 1
fi

if [[ "$(. /etc/os-release && echo "$ID")" != "ubuntu" ]]; then
  echo "此脚本只支持 Ubuntu。" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git rsync ufw docker.io docker-compose-v2
systemctl enable --now docker

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "Ubuntu 部署底座已准备好：Docker、Compose、Git、rsync 和 UFW。"
