FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for persistence
RUN mkdir -p /app/memory_db /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CHROMA_PATH=/app/memory_db

# Expose port (if needed for health checks)
EXPOSE 8080

# Run the agent
CMD ["python", "agent.py", "start"]
