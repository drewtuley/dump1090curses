# ---- builder: build wheels to avoid building in final image ----
FROM python:3.11-slim-bullseye AS builder

# Install build deps for packages that compile (cryptography, psycopg2-binary, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    gcc \
    libffi-dev \
    libssl-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels

# Upgrade pip / wheel tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy only requirements first to leverage layer cache
COPY requirements.txt /wheels/requirements.txt

# Build wheels for all requirements (this avoids building on runtime)
RUN pip wheel --wheel-dir=/wheels/wheels -r requirements.txt

# ---- final image ----
FROM python:3.11-slim-bullseye

# Create non-root user
ENV APP_USER=app
RUN groupadd --gid 1000 $APP_USER || true \
 && useradd --uid 1000 --gid 1000 -m -s /bin/bash $APP_USER || true

# Install runtime deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /wheels/wheels /wheels/wheels
COPY --from=builder /wheels/requirements.txt /wheels/requirements.txt

# Install packages from wheels (fast, no compilation)
RUN python -m pip install --upgrade pip \
 && pip install --no-index --find-links=/wheels/wheels -r /wheels/requirements.txt \
 && rm -rf /wheels

# Copy app source
COPY src/dump1090curses/regserver.py  /app
COPY src/dump1090curses/PyRadar.py /app

# Make sure files owned by non-root user
RUN chown -R $APP_USER:$APP_USER /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Gunicorn tuning defaults (override at runtime)
    WEB_CONCURRENCY=3 \
    PORT=5001

EXPOSE 5001

USER $APP_USER

# Default Gunicorn command - override in compose or docker run if you like
# The module name below assumes your entrypoint is `myproject:app`
# You can change `myproject:app` to your module (eg. wsgi:app)
ENV GUNICORN_CMD="gunicorn --workers ${WEB_CONCURRENCY} --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile --preload - regserver:create_app()"

# Use a small shell so env var expands
CMD ["sh", "-c", "$GUNICORN_CMD"]
