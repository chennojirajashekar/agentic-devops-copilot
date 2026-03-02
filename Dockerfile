# Agentic DevOps Copilot - Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Environment variables (override at runtime)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Expose port (if adding API server later)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import orchestrator; print('OK')" || exit 1

# Default command
CMD ["python", "main.py"]
