## MiniZapier Runbook (сервер)

### Где лежит деплой

- Каталог деплоя: `${DEPLOY_PATH}` (см. secrets GitHub Actions)
- В каталоге должны быть: `.env`, `docker-compose.prod.yml`

### Деплой (обновить контейнеры)

```bash
cd /path/to/deploy
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml down --remove-orphans
docker compose -f docker-compose.prod.yml up -d
```

### Миграции

```bash
cd /path/to/deploy
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### Логи

```bash
cd /path/to/deploy
docker compose -f docker-compose.prod.yml logs -f --tail=200 web
docker compose -f docker-compose.prod.yml logs -f --tail=200 worker
docker compose -f docker-compose.prod.yml logs -f --tail=200 beat
```

### Проверить статус контейнеров

```bash
cd /path/to/deploy
docker compose -f docker-compose.prod.yml ps
```

### Частые проблемы

- **CSRF ошибки / DisallowedHost**: проверь `.env`:
  - `SITE_DOMAIN`
  - `DJANGO_ALLOWED_HOSTS`
  - `DJANGO_CSRF_TRUSTED_ORIGINS`

- **После обновления “едет” интерфейс**: увеличь `STATIC_VERSION` в `.env`, перезапусти `web`.

```bash
cd /path/to/deploy
sed -i 's/^STATIC_VERSION=.*/STATIC_VERSION=5/' .env
docker compose -f docker-compose.prod.yml up -d
```

