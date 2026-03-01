FROM python:3.11-slim

WORKDIR /app

# System deps (make is needed for the CMD)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (non-editable for Docker)
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[all]"

# Copy remaining project files
COPY Makefile .
COPY README.md .

# Default: run full pipeline
CMD ["make", "all"]
