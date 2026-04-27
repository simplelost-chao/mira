FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv --no-cache-dir

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source
COPY vibe/ ./vibe/
COPY static/ ./static/

EXPOSE 8888

CMD ["uv", "run", "vibe", "serve"]
