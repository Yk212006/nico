FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="NICO Cloud Assistant"
LABEL org.opencontainers.image.description="AI-powered cloud assistant with Google integrations"
LABEL org.opencontainers.image.version="0.2.0"

WORKDIR /app

# Install system dependencies for some optional packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README_NICO.md ./
COPY nico/ nico/
COPY credentials.json ./

# Install NICO with web dependencies
RUN pip install --no-cache-dir -e .[web,google]

# Expose the web API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/api/health').raise_for_status()"

# Run with uvicorn
CMD ["python", "-m", "nico.web_api"]
