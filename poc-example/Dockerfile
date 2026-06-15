# syntax=docker/dockerfile:1

############################
# 1) Builder stage
############################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /service

# System deps for uv
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

# Install uv (official installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy only dependency files first to maximize layer caching
COPY pyproject.toml uv.lock ./

# Create a virtualenv and sync deps from lock
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN uv sync --frozen --no-dev --active

############################
# 2) Runtime stage
############################
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

WORKDIR /service

# Install uv in runtime stage
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy dependency files and application code
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

CMD ["python"]
