# Use official Python runtime as base image
# Using python:3.11-slim for better compatibility with pipecat-ai
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libsndfile1 \
    ffmpeg \
    portaudio19-dev \
    python3-dev \
    build-essential \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy Google credentials file
# Note: Place your Google credentials JSON file as 'google-credentials.json' in the project root
COPY grounded-jetty-465206-c8-ca51e124a8bd.json ./google-credentials.json

# Copy the application code
COPY app/ ./app/
COPY run.py .


# Create a non-root user to run the application
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "run.py"]

