# Create requirements.txt from poetry dependencies
FROM python:3.10-slim AS requirements

WORKDIR /tmp

RUN pip install poetry

# Copy poetry.lock* in case it doesn't exist in the repo
COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes


# Stage used in production
FROM python:3.10 AS production

WORKDIR /app/

ENV PROVIDERS_CONF_DIR=/providers-conf

COPY --from=requirements /tmp/requirements.txt /app/requirements.txt

# Updating packages and installing cron
RUN apt-get update \
    && apt-get install -y docker.io \
    && apt-get clean

# Upgrade pip and install requirements
RUN pip install --user --upgrade pip \
    && pip install --user --no-cache-dir --upgrade -r /app/requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/app/src"

COPY ./src /app/src
