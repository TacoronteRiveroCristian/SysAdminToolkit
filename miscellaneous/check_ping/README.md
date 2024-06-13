# Ping con Telegraf e InfluxDB

Este proyecto contiene los scripts y configuraciones necesarios para realizar pings a dispositivos y almacenar los resultados en una base de datos InfluxDB. El propósito es monitorear la disponibilidad y el tiempo de respuesta de varios dispositivos de red y almacenar estos datos para su posterior análisis.

## Contenido

- `docker-compose.yaml`: Archivo de configuración para Docker Compose, que facilita la orquestación de contenedores Docker necesarios para el proyecto.
- `.env`: Archivo de variables de entorno que contiene las configuraciones necesarias para la base de datos InfluxDB y otros servicios.
- `init-influxdb.sh`: Script de inicialización para configurar InfluxDB, crear un usuario administrador y habilitar la autenticación HTTP.

## Prerrequisitos

Antes de comenzar, asegúrate de tener instalados los siguientes requisitos:

- Docker
- Docker Compose

## Configuración

1. Configurar el archivo `.env`:

- `INFLUXDB_PORT`: Especifica el puerto en el que InfluxDB escuchará las conexiones. El valor predeterminado es 8086.
- `INFLUXDB_HTTP_AUTH_ENABLED`: Indica si la autenticación HTTP está habilitada en InfluxDB. Establece true para habilitarla.
- `INFLUXDB_ADMIN_USER`: Define el nombre de usuario del administrador de InfluxDB. Este usuario tendrá privilegios administrativos.
- `INFLUXDB_ADMIN_PASSWORD`: Especifica la contraseña para el usuario administrador definido en INFLUXDB_ADMIN_USER.
- `TELEGRAF_NAME_DATABASE`: Nombre de la base de datos que será utilizada por Telegraf para almacenar los datos de los pings.

2. Modificar el fichero `telegraf.conf` según los requisitos del proyecto.

3. Ejecutar el comando `docker-compose up -d` junto con el archivo `.env` para desplegar los servicios.