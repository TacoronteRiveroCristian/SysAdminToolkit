FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instalar cron para backups programados
RUN apt-get update && apt-get -y install cron && rm -rf /var/lib/apt/lists/*

# Copiar requisitos e instalar dependencias
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ .

# Hacer scripts ejecutables
RUN chmod +x /app/backup_influxdb.py /app/backup_influxdb_cron.py

# Crear directorio de logs
RUN mkdir -p /var/log/backup_influxdb

# El archivo de configuración YAML se monta como volumen
# desde el host en docker-compose.yaml

# Comando por defecto (ejecuta el script principal)
CMD ["python", "/app/backup_influxdb.py"]
