# SysAdminToolkit - Monitorización del Sistema

Esta carpeta contiene scripts y configuraciones para la monitorización de sistemas basados en Linux, incluyendo Ubuntu y Raspbian. Utiliza Docker Compose para desplegar servicios de monitorización como Prometheus, Node Exporter y Grafana.

## Configuración de Variables de Entorno

El archivo `.env` contiene todas las variables de entorno necesarias para configurar los servicios. Además, para que no haya conflictos al desplegar los servicios, hay que tener en cuenta que Docker Compose busca por defecto el archivo `.env` en el mismo path que el fichero `docker-compose.yaml`. A continuación, se detallan cada una de las variables y su propósito:

### Node Exporter

- **NODE_EXPORTER_PORT**: Puerto en el que Node Exporter expondrá las métricas.
  - Valor predeterminado: `9100`

### Prometheus

- **PROMETHEUS_PORT**: Puerto en el que Prometheus expondrá su interfaz web.
  - Valor predeterminado: `9090`
- **PROMETHEUS_NAME_DATASOURCE**: Nombre del Data Source en Grafana para Prometheus.
  - Ejemplo: `DS_PROMETHEUS`
- **PROMETHEUS_TIME_SCRAP**: Intervalo de scraping para Prometheus.
  - Ejemplo: `30s`
- **PROMETHEUS_RETENTION_TIME**: Tiempo de retención de los datos en Prometheus.
  - Ejemplo: `7d`

### Grafana

- **GRAFANA_PORT**: Puerto en el que Grafana expondrá su interfaz web.
  - Valor predeterminado: `3000`
- **GRAFANA_ENABLED_SMTP**: Habilitar o deshabilitar el SMTP para notificaciones en Grafana.
  - Valores: `true` o `false`
- **GRAFANA_HOST_SMTP**: Dirección del servidor SMTP.
  - Ejemplo: `smtp.gmail.com:587`
- **GRAFANA_USER_SMTP**: Usuario para el servidor SMTP.
  - Ejemplo: `example@gmail.com`
- **GRAFANA_PASSWORD_SMTP**: Contraseña o token para el servidor SMTP.
  - Ejemplo: `mytoken`
- **GRAFANA_ADDRES_HOST_SMTP**: Dirección del remitente de los correos SMTP.
  - Ejemplo: `example@gmail.com`
- **GRAFANA_EMAILS_TO_NOTIFY**: Correos electrónicos que recibirán las notificaciones.
  - Ejemplo: `example@gmail.com`
- **GRAFANA_INTERVAL_ALERT**: Intervalo de tiempo para enviar alertas.
  - Ejemplo: `3m`
- **GRAFANA_TRESHOLD_CPU_PERCENT**: Umbral de uso de CPU para alertas.
  - Ejemplo: `0.8`
- **GRAFANA_TRESHOLD_RAM_PERCENT**: Umbral de uso de RAM para alertas.
  - Ejemplo: `0.2`
- **GRAFANA_TRESHOLD_DISK_PERCENT**: Umbral de uso de disco para alertas.
  - Ejemplo: `0.8`
- **GRAFANA_TRESHOLD_TEMP_CELCIUS**: Umbral de temperatura en grados Celsius para alertas.
  - Ejemplo: `70`
- **GF_SECURITY_ADMIN_USER**: Usuario administrador para Grafana.
  - Valor predeterminado: `admin`
- **GF_SECURITY_ADMIN_PASSWORD**: Contraseña para el usuario administrador de Grafana.
  - Valor predeterminado: `admin_2`

## Ejecución de Docker Compose

Para ejecutar Docker Compose con las variables de entorno definidas en el archivo `.env`, sigue estos pasos:

1. **Crear el archivo `.env`**: En el directorio raíz del proyecto, crea un archivo llamado `.env` y copia las variables de entorno proporcionadas en él.

   ```plaintext
   NODE_EXPORTER_PORT=9100

   PROMETHEUS_PORT=9090
   PROMETHEUS_NAME_DATASOURCE=DS_PROMETHEUS
   PROMETHEUS_TIME_SCRAP=30s
   PROMETHEUS_RETENTION_TIME=7d

   GRAFANA_PORT=3000
   GRAFANA_ENABLED_SMTP=false
   GRAFANA_HOST_SMTP=smtp.gmail.com:587
   GRAFANA_USER_SMTP=example@gmail.com
   GRAFANA_PASSWORD_SMTP=mytoken
   GRAFANA_ADDRES_HOST_SMTP=example@gmail.com
   GRAFANA_EMAILS_TO_NOTIFY=example@gmail.com
   GRAFANA_INTERVAL_ALERT=3m
   GRAFANA_TRESHOLD_CPU_PERCENT=0.8
   GRAFANA_TRESHOLD_RAM_PERCENT=0.2
   GRAFANA_TRESHOLD_DISK_PERCENT=0.8
   GRAFANA_TRESHOLD_TEMP_CELCIUS=70
   GF_SECURITY_ADMIN_USER=admin
   GF_SECURITY_ADMIN_PASSWORD=admin_2
    ```

2. Desplegar los servicios con el siguiente comando teniendo en cuenta que se debe de encontrar en el mismo path que el archivo `.env` y `docker-compose.yaml`:

    ```bash
    docker-compose up -d
    ```


## Notas Adicionales

- **Interpolación de Variables de Entorno**: Asegúrate de que Docker Compose está configurado para cargar variables del archivo `.env`.
- **Compatibilidad de Variables**: Las variables de entorno en el archivo `.env` deben coincidir exactamente con las que se referencian en los archivos de configuración de Docker Compose y Grafana.
- **Permisos de Archivo**: Asegúrate de que el archivo `.env` y los archivos de configuración tienen los permisos adecuados para ser leídos por Docker Compose.
