#!/bin/sh
set -eu
cd /workspace/tvip-stb-appstore
if [ ! -f .env ]; then
    (
        umask 077
        {
            printf 'POSTGRES_PASSWORD='
            openssl rand -hex 24
            printf 'DJANGO_SECRET_KEY='
            openssl rand -hex 32
        } > .env
    )
fi
docker compose build web
docker compose up -d db
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py collectstatic --noinput
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py makemigrations --check --dry-run
