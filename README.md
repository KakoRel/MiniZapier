# MiniZapier

**English:** Self-hosted workflow automation (like a mini Zapier): visual editor (Vue Flow), Django backend, Celery + Redis, PostgreSQL.

**Русский:** Платформа для визуальных сценариев автоматизации: редактор на **Vue 3 + Vite + Vue Flow**, API на **Django**, очереди **Celery + Redis**, БД **PostgreSQL**.

## Requirements

- Python 3.12+ (project uses 3.14 locally; pin in production if needed)
- Node.js 20+ (for `frontend` build)
- Docker Desktop (Postgres + Redis for local dev on Windows)

## Quick start (local)

1. **Clone** the repo. **Do not commit secrets** — copy env from example only on your machine:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`: `DJANGO_SECRET_KEY`, database URL, etc.

2. **Start** Postgres and Redis:

   ```bash
   docker compose up -d
   ```

   Postgres is mapped to host port **5433** (avoids conflict with a local PostgreSQL on 5432). Match `POSTGRES_PORT` in `.env`.

3. **Build** the workflow editor (output goes to `backend/static/workflow_editor/`, ignored by git):

   ```bash
   cd frontend
   npm ci
   npm run build
   ```

4. **Migrate** and run:

   ```bash
   cd backend
   python -m venv ../.venv
   ../.venv/bin/pip install -r ../requirements.txt
   ../.venv/bin/python manage.py migrate
   ../.venv/bin/python manage.py createsuperuser
   ../.venv/bin/python manage.py runserver
   ```

   On Windows PowerShell, use `..\.venv\Scripts\python` instead of `../.venv/bin/python`.

5. Open: `/` (home), `/workflows/` (after login), `/accounts/signup/`.

`MAIL_ENABLED=0` in `.env` disables email and email verification (dev-friendly). Set `MAIL_ENABLED=1` and `EMAIL_*` for production mail.

## Frontend dev (optional)

```bash
cd frontend && npm run dev
```

For full save/load with Django, prefer `npm run build` and use the editor inside Django.

## Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Configure environment on the server (no secrets in the image). GitHub Actions deploy expects repository secrets: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `DEPLOY_PATH` (non-secret path is OK in secrets; use a dedicated deploy key with minimal permissions).

## Security checklist before pushing

- Never commit `.env` (it is listed in `.gitignore`).
- Do not commit real `DJANGO_SECRET_KEY`, DB passwords, SMTP passwords, or API keys.
- Use `.env.example` only with placeholders.
- After `git status`, confirm `.env` is **not** listed; if it was ever committed, rotate keys and remove it from history (`git filter-repo` or BFG).

## License

(Add your license if applicable.)
