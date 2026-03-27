FROM public.ecr.aws/docker/library/node:20-slim AS frontend_builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json /app/frontend/
WORKDIR /app/frontend
RUN npm ci

COPY frontend /app/frontend
COPY backend /app/backend
RUN npm run build


FROM public.ecr.aws/docker/library/python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY --from=frontend_builder /app/backend/static/workflow_editor /app/backend/static/workflow_editor

WORKDIR /app/backend
ENV DJANGO_SETTINGS_MODULE=config.settings

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

