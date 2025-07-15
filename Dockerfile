# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Create virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY pyproject.toml /tmp/
COPY requirements/ /tmp/requirements/
WORKDIR /tmp
RUN uv pip install -r requirements/prod.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application user
RUN groupadd -r openlogistics && \
    useradd -r -g openlogistics openlogistics

# Create application directory
WORKDIR /app

# Copy application code
COPY src/ /app/src/
COPY pyproject.toml README.md /app/

# Install application
RUN pip install -e .

# Change ownership to application user
RUN chown -R openlogistics:openlogistics /app

# Switch to application user
USER openlogistics

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import open_logistics; print('OK')" || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["openlogistics", "--help"]
