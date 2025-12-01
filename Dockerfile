FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy server
COPY server/ .

# Create necessary directories
RUN mkdir -p /app/logs /app/data

EXPOSE 9009

CMD ["python", "main.py"]
