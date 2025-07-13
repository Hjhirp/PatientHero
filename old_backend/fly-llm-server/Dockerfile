# Use Python base image that's compatible with Fly.io
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV HF_HOME=/app/cache
ENV TRANSFORMERS_CACHE=/app/cache

# Create cache directory
RUN mkdir -p /app/cache

# Run the application
CMD ["python", "server.py"]
