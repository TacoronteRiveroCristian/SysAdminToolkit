FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install cron for scheduled backups
RUN apt-get update && apt-get -y install cron && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ .

# Make scripts executable
RUN chmod +x /app/backup_influxdb.py /app/backup_influxdb_cron.py

# Create log directory
RUN mkdir -p /var/log/backup_influxdb

# Default command (can be overridden)
CMD ["python", "/app/backup_influxdb.py"]
