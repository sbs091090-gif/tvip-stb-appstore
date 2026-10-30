# TVIP Android Appstore

Сервер каталога TVIP protoVersion=1, PostgreSQL и Django admin.
Выбор версии по IPv4/IPv6 CIDR, заранее собранные JSON/ETag в памяти,
прямая раздача APK и медиа через Nginx. Формат — по примеру из ТЗ.

## Запуск (все сборки и тесты в Docker)

Нужны Docker Engine и Docker Compose v2. Используйте существующий checkout;
задачи cloud уже изолированы, отдельный Git worktree не требуется.

1. Скопируйте `.env.example` в `.env`, замените оба секрета на случайные значения.
   Для локальной генерации подходят `openssl rand -hex 32`. Не коммитьте `.env`.
2. Выполните в корне репозитория:

```sh
docker compose build web
docker compose up -d db
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py collectstatic --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose up -d --wait web nginx
```

В managed cloud Docker-команды могут требовать разрешённого запуска с расширенными
правами для доступа к socket. Не запускайте второй dockerd.
Сборка использует BuildKit secret `proxy_ca` (системный CA bundle по умолчанию).
При корпоративном proxy задайте BUILD_CA_BUNDLE с доверенным bundle, не отключайте TLS.

Пути: `/admin/`, `/catalog.json`, `/healthz` на порту 8080.
Администратор создаёт приложение с точным package name, загружает APK в Releases,
отмечает одну default-версию и добавляет Target rules для альтернативных версий.
Более узкая подсеть имеет приоритет. Загрузка несовпадающего package отклоняется.
Иконка, баннер 16:9 и скриншоты задаются у приложения; оформление оператора —
в Store settings. Публикация изменений в памяти занимает до 2 секунд плюс время сборки.

## Проверки

```sh
docker compose run --rm web python manage.py test tests --verbosity 2
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web python manage.py check
```

Основные тесты используют настоящую PostgreSQL test database; приложение не должно
подключаться к production БД при их выполнении. Положительные тесты извлечения APK
требуют отдельного fixture и без него явно пропускаются. Для воспроизводимой проверки:

```sh
curl -fsSL https://raw.githubusercontent.com/androguard/androguard/v4.1.3/tests/data/APK/hello-world.apk -o /tmp/tvip-test.apk
chmod 644 /tmp/tvip-test.apk
printf '%s\n' 'f427a0ebe0bca97b9acf6cd2a2a01c37a7d3762841810fc54a7191ec637330b2  /tmp/tvip-test.apk' | sha256sum -c -
docker compose run --rm -e APK_FIXTURE=/tmp/test.apk -v /tmp/tvip-test.apk:/tmp/test.apk:ro web python manage.py test tests --verbosity 2
```

Fixture относится к тестовым данным Androguard; он не публикуется в рабочем каталоге.
Тесты покрывают CIDR, longest prefix, IPv6, независимое наследование приложений,
ETag/304/HEAD, ошибки запроса, ограничения БД, права админки, обновление snapshot
и отсутствие SQL при выборе каталога. С fixture проверяются binary manifest и
загрузка через авторизованную форму admin с сохранением файла.

`requirements.txt` задаёт прямые зависимости, `requirements.lock` фиксирует полное
проверенное окружение; Docker устанавливает lock. Обновление зависимостей выполняйте
в контейнере с повторным запуском тестов.

[Архитектура и эксплуатационные ограничения](docs/architecture.md).

Для повторной подготовки текущей cloud-среды предусмотрен `sh scripts/install.sh`.
Он использует `/workspace/tvip-stb-appstore`, сохраняет существующий `.env`,
а при его отсутствии создаёт локальные случайные секреты. Скрипт не создаёт
администратора и не запускает Nginx: выполните `createsuperuser` и `up` из инструкции.
После запуска сервисов функциональная проверка через настоящий Nginx:

```sh
docker compose exec -T web python -m tests.smoke
```

Ограниченный HTTP benchmark (только условные запросы каталога, без скачивания APK):

```sh
docker compose exec -T web python tests/load.py --requests 30000 --concurrency 100
```

Результат включает число приложений, RPS и p95/p99. Для приёмки нагрузки заполните
каталог рабочими данными и отдельно испытайте скачивание APK; пустой каталог
подходит только для исходного измерения HTTP-пути.
