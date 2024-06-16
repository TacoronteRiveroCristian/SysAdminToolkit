
# InfluxDB Backup Script

Este script permite realizar copias de seguridad de múltiples bases de datos y mediciones de InfluxDB 1.8. Se encarga de copiar los datos nuevos desde la última entrada copiada, asegurando que no se dupliquen registros y se manejen de manera eficiente.

## Requisitos

- Python 3.x
- Paquetes Python:
  - `influxdb`
  - `python-dotenv`

## Instalación

1. Clona este repositorio o descarga los archivos.
2. Instala los paquetes necesarios utilizando `pip`:

   ```bash
   pip install influxdb python-dotenv
   ```

3. Crea un archivo `.env` en el mismo directorio que el script con el siguiente contenido (puedes ajustar las variables según sea necesario):

   ```env
   SOURCE_URL=http://source-influxdb:8086
   SOURCE_DBS=source_db1,source_db2,source_db3
   DEST_URL=http://destination-influxdb:8086
   DEST_DBS=dest_db1,dest_db2,dest_db3
   LOG_FILE=backup_log.log
   ```

## Uso

1. Asegúrate de que los valores en el archivo `.env` están correctamente configurados:
   - `SOURCE_URL`: URL de la instancia de InfluxDB de origen.
   - `SOURCE_DBS`: Comma-separated list de las bases de datos de origen.
   - `DEST_URL`: URL de la instancia de InfluxDB de destino.
   - `DEST_DBS`: Comma-separated list de las bases de datos de destino correspondientes.
   - `LOG_FILE`: Nombre del archivo de log.

2. Ejecuta el script:

   ```bash
   python backup_influxdb_v1_8.py
   ```

3. El script realizará las siguientes acciones:
   - Conectarse a las bases de datos de origen y destino.
   - Iterar sobre cada base de datos y sus mediciones.
   - Copiar los datos nuevos desde la última entrada copiada.
   - Registrar las operaciones y errores en el archivo de log especificado.

## Ejemplo de archivo `.env`

```env
SOURCE_URL=http://localhost:8086
SOURCE_DBS=db1,db2,db3
DEST_URL=http://localhost:8086
DEST_DBS=db1_backup,db2_backup,db3_backup
LOG_FILE=backup_log.log
```

## Funciones principales

### `backup_measurements_individually`

Realiza copias de seguridad para cada medición individualmente.

### `get_last_entry_time`

Obtiene el último registro de una medición específica en la base de datos destino.

### `copy_data_since_last_entry_for_measurement`

Copia los datos desde la base de datos origen a la base de datos destino para una medición específica, comenzando desde el último registro copiado.

## Mantenimiento

Revisa el archivo de log `backup_log.log` para verificar el estado de las copias de seguridad y detectar posibles errores.

---

Este script está diseñado para ser ejecutado periódicamente, por ejemplo, cada 30 minutos, usando un cron job o cualquier otro sistema de tareas programadas. Asegúrate de que el script se ejecuta en un entorno donde pueda acceder a las instancias de InfluxDB configuradas.
