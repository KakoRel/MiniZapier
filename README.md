# MiniZapier

Платформа для визуальных сценариев автоматизации (похожа на mini Zapier): редактор на **Vue 3 + Vite + Vue Flow**, API на **Django**, очереди **Celery + Redis**, БД **PostgreSQL**.

## Требования

- Python 3.12+ (локально используется 3.14; в проде можно закрепить версию)
- Node.js 20+ (для сборки `frontend`)
- Docker Desktop (для локальной разработки: Postgres + Redis)

## Быстрый старт (локально)

1. Склонируй репозиторий. **Не коммить секреты** — копируй env только у себя:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`: `DJANGO_SECRET_KEY`, database URL, etc.

2. Подними Postgres и Redis:

   ```bash
   docker compose up -d
   ```

Postgres прокинут на хостовый порт **5433** (чтобы не конфликтовать с локальным PostgreSQL на **5432**). Проверь `POSTGRES_PORT` в `.env`.

3. Собери редактор (результат попадает в `backend/static/workflow_editor/` и игнорируется git):

   ```bash
   cd frontend
   npm ci
   npm run build
   ```

4. Прогони миграции и запусти проект:

   ```bash
   cd backend
   python -m venv ../.venv
   ../.venv/bin/pip install -r ../requirements.txt
   ../.venv/bin/python manage.py migrate
   ../.venv/bin/python manage.py createsuperuser
   ../.venv/bin/python manage.py runserver
   ```

В Windows PowerShell используй `..\.venv\Scripts\python` вместо `../.venv/bin/python`.

5. Открой:
- `/` — главная
- `/workflows/` — список сценариев (после входа)
- `/accounts/signup/` — регистрация

`MAIL_ENABLED=0` в `.env` отключает почту и подтверждение email (удобно для разработки). Для реальной почты включи `MAIL_ENABLED=1` и заполни `EMAIL_*`.

## Разработка фронтенда (опционально)

```bash
cd frontend && npm run dev
```

Для полного save/load с Django удобнее собирать (`npm run build`) и пользоваться редактором внутри Django.

## Прод (docker compose)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

После запуска приложение будет доступно по хостовому порту `8001` (контейнерный `8000`).

На Ubuntu для деплоя нужен **Docker Compose v2** (команда `docker compose`, пакет `docker-compose-plugin`). Старый `docker-compose` 1.29.x с новым Docker Engine при `up --force-recreate` может падать с `KeyError: 'ContainerConfig'`.

```bash
sudo apt-get update
sudo apt-get install -y docker-compose-plugin
docker compose version
```

Задай переменные окружения на сервере (секреты не должны попасть в образ). GitHub Actions deploy ожидает secrets репозитория: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `DEPLOY_PATH` (путь на сервере можно указывать среди secrets; лучше использовать отдельный deploy key с минимальными правами).

## Чеклист безопасности перед пушем

- Не коммить `.env` (он добавлен в `.gitignore`).
- Не коммить реальные `DJANGO_SECRET_KEY`, пароли к БД, пароли SMTP и любые API-ключи.
- Используй `.env.example` только с заглушками.
- Перед коммитом проверь `git status`: `.env` **не должен** быть в списке. Если секреты всё-таки попали в историю — ключи нужно перевыпустить и очистить историю (`git filter-repo` или BFG).

## Лицензия

Добавь лицензию, если это нужно.
