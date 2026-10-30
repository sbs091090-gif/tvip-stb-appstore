# Проверка в cloud-среде — 30 октября 2026

Все сборки, миграции, тесты и HTTP-проверки выполнены внутри Docker/Compose.

- Полный набор: 21 тест, 21 passed, 0 skipped, 0 failed.
- Включены положительные проверки binary manifest и загрузки APK через admin.
  Fixture: Androguard v4.1.3 hello-world.apk,
  SHA-256 f427a0ebe0bca97b9acf6cd2a2a01c37a7d3762841810fc54a7191ec637330b2.
- PostgreSQL: миграции применены; повторный запуск не требует миграций.
- Django check и makemigrations --check --dry-run: успешно.
- Повторный collectstatic: 127 файлов не изменены.
- Проверены scripts/install.sh и scripts/start.sh.
- Nginx smoke: health 200, JSON protoVersion=1, conditional GET 304,
  перезапись X-Real-IP, CSS админки 200, Range media 206 с ожидаемыми байтами.

## Базовый HTTP benchmark

Команда в контейнере web: `python tests/load.py --requests 30000 --concurrency 100`.

| Параметр | Результат |
|---|---:|
| Условные GET | 30 000 |
| Параллелизм | 100 |
| Приложений в каталоге | 0 |
| Время | 12,062 с |
| Запросов/с | 2487,2 |
| p95 | 52,11 мс |
| p99 | 66,76 мс |

Все запросы завершились ожидаемым HTTP 304. Это базовое измерение HTTP-пути в
данной машине, без рабочего каталога, большого набора правил или скачивания APK.
Оно не подтверждает ёмкость 30 000 одновременных соединений и production SLA.

GitHub Actions workflow добавлен, но удалённый CI ещё не запускался.
Физическая TVIP S-Box, внешний HTTPS, восстановление из резервной копии и
готовность нового опубликованного экземпляра в эту проверку не входили.
