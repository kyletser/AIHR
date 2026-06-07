#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/AIHR}"

if ! command -v docker >/dev/null 2>&1; then
  dnf update -y
  dnf install -y docker docker-compose-plugin git
  systemctl enable docker
  systemctl start docker
fi

cd "$APP_DIR"

if [ ! -f .env.production ]; then
  cp .env.production.example .env.production
  echo "Created .env.production. Edit it before starting:"
  echo "  nano $APP_DIR/.env.production"
  exit 1
fi

docker compose --env-file .env.production up -d --build
docker compose ps

echo
echo "OfferCatcher should be available on:"
echo "  http://SERVER_IP:${FRONTEND_PORT:-8088}"
