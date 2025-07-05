# InfluxDB Backup System Dockerfile
# ==================================
#
# Contenedor para el sistema de backup de InfluxDB que permite
# ejecutar múltiples procesos de backup en paralelo basados en
# configuraciones YAML.

FROM python:3.11-slim

# Metadata
LABEL maintainer="InfluxDB Backup System"
LABEL description="Multi-process InfluxDB backup system with YAML configuration"
LABEL version="1.0.0"

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN groupadd -r influxbackup && useradd -r -g influxbackup influxbackup

# Crear directorios necesarios
RUN mkdir -p /app /config /var/log/backup_influxdb \
    && chown -R influxbackup:influxbackup /app /config /var/log/backup_influxdb

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY main.py .

# Hacer ejecutable el script principal
RUN chmod +x main.py

# Cambiar al usuario no-root
USER influxbackup

# Crear punto de montaje para configuraciones
VOLUME ["/config", "/var/log/backup_influxdb"]

# Configurar healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python main.py --validate-only || exit 1

# Punto de entrada
ENTRYPOINT ["python", "main.py"]

# Comando por defecto
CMD ["--config", "/config"]
