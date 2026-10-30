#!/bin/sh
set -eu
cd /workspace/tvip-stb-appstore
docker compose up -d --wait web nginx
docker compose exec -T nginx nginx -t
docker compose exec -T nginx nginx -s reload
docker compose exec -T web python -m tests.smoke
