FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# python-oracledb "thin" mode needs no Oracle Instant Client or libaio.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./scripts ./scripts
COPY ./rule_packs ./rule_packs
COPY ./contracts ./contracts

# Alembic is the only schema change path, so the migrations and their config
# must be in the image. Without them the container cannot bring a database
# up to the revision the code expects.
COPY ./alembic.ini ./alembic.ini
COPY ./migrations ./migrations

# Migrations run as a release step, before the server binds. If one fails the
# container exits non-zero, the deploy is marked failed, and the previous
# (working) deployment keeps serving. The alternative — migrating in the
# background after the server has already started accepting traffic — can
# serve a schema that is behind the code.
#
# The administrator password reset is deliberately NOT part of the container
# start. Starting a container must never change an existing administrator's
# password. Operators run `python -m scripts.reset_admin_password` by hand,
# inside a running container, when recovery is genuinely needed.
#
# `exec` makes uvicorn the container's PID 1 so it receives SIGTERM directly.
ENV MIGRATE_ON_STARTUP=false

# Render injects PORT; default to 8000 for local/docker-compose use.
ENV PORT=8000
EXPOSE 8000

# Public liveness probe. /health is unauthenticated by design (platform
# health check), so the container check needs no credentials. Python is
# used instead of curl/wget because python:3.11-slim ships neither.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','8000')}/health\",timeout=4)" || exit 1

CMD ["sh", "-c", "python -m scripts.migrate upgrade && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
