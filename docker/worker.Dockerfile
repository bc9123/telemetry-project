FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY app /app/app

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir -e .

COPY . /app

CMD ["celery", "-A", "app.workers.celery_app:celery_app", "worker", "--loglevel=INFO"]
