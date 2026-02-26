FROM python:3.13.3-slim@sha256:56a11364ffe0fee3bd60af6d6d5209eba8a99c2c16dc4c7c5861dc06261503cc

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --default-timeout=600 --retries=10 -r requirements.txt

# Copy application code
COPY . .

# Create data directory for FAISS index
RUN mkdir -p /app/data

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 9000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]
