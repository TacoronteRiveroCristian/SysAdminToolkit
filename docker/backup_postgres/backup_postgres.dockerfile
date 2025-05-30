FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instalar cron y cliente PostgreSQL
RUN apt-get update && \
    apt-get -y install cron postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Copiar requisitos e instalar dependencias Python
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ .

# Hacer scripts ejecutables
RUN chmod +x /app/backup_postgres.py /app/backup_postgres_cron.py

# Crear directorio de logs
RUN mkdir -p /var/log/backup_postgres

# El archivo de configuración YAML se monta como volumen
# desde el host en docker-compose.yaml

# Comando por defecto (ejecuta el script principal o duerme)
# El script de entrada decidirá si ejecutar backup_postgres.py o backup_postgres_cron.py
CMD ["sleep", "infinity"]
