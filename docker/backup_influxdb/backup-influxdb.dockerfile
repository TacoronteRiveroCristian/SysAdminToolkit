FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instalar cron para backups programados
RUN apt-get update && apt-get -y install cron && rm -rf /var/lib/apt/lists/*

# Copiar requisitos e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ .

# Crear directorio de logs
RUN mkdir -p /var/log/backup_influxdb

# Copiar carpeta de ficheros .YAML
COPY config/ .

# Comando por defecto (ejecuta el script principal)
CMD ["sleep", "infinity"]
