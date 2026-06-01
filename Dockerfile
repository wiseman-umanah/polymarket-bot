FROM python:3.12-slim

WORKDIR /app

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first — this layer is cached until lockfile changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy source and install the project itself
COPY . .
RUN uv sync --frozen

CMD ["uv", "run", "polymarket-bot"]
