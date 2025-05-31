# PostgreSQL Backup to CSV

Este script se conecta a una base de datos PostgreSQL, extrae datos de las tablas y los guarda en formato CSV. Los CSVs se organizan por fecha (si la tabla tiene una columna de fecha adecuada) o se paginan, y finalmente se comprimen en un archivo ZIP.

## Configuración

Sigue estos pasos para configurar y ejecutar el script:

1.  **Navegar al Directorio del Script:**
    Abre una terminal y navega al directorio donde has guardado los archivos de este script (ej: `path/to/your_script_directory/`). Todos los comandos siguientes se deben ejecutar desde este directorio.

2.  **Crear un Entorno Virtual (Recomendado):**
    ```bash
    python -m venv venv
    ```
    Activa el entorno virtual:
    *   En Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    *   En macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Instalar Dependencias:**
    Con el entorno virtual activado, instala las librerías necesarias:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar la Conexión a la Base de Datos (`config.ini`):**
    Edita el archivo `config.ini` (que debe estar en este mismo directorio del script) con los detalles de tu servidor PostgreSQL:
    ```ini
    [postgresql]
    db_host = TU_HOST_IP  # Ej: 10.8.0.10 o localhost
    db_port = 5432
    db_name = TU_NOMBRE_DE_BASE_DE_DATOS
    db_user = TU_USUARIO
    db_password = TU_CONTRASEÑA
    ```

5.  **Configurar Parámetros del Script (`main.py`):**
    Abre el archivo `main.py` (en este mismo directorio) y ajusta las siguientes constantes según tus necesidades:
    *   `START_DATE_STR`: Fecha de inicio para la extracción (formato "YYYY-MM-DD"). Si es `None`, se infiere de la tabla o se extrae todo.
    *   `END_DATE_STR`: Fecha de fin para la extracción (formato "YYYY-MM-DD"). Si es `None`, se infiere de la tabla o se extrae todo.
    *   `DATE_COLUMN_NAME`: Nombre de la columna que contiene la fecha/timestamp para la segmentación diaria (ej: "date_hour").
    *   `MAX_ROWS_PER_CSV`: Número máximo de filas por archivo CSV para tablas sin columna de fecha o para paginación general.
    *   `DB_SCHEMA`: Esquema de la base de datos del cual se extraerán las tablas (ej: "public").

## Uso

Una vez completada la configuración:

1.  Asegúrate de que tu entorno virtual (si creaste uno) está activado.
2.  Verifica que tu terminal está en el directorio del script (donde se encuentra `main.py`).
3.  Ejecuta el script:
    ```bash
    python main.py
    ```

## Resultado

El script realizará las siguientes acciones:

*   Se conectará a la base de datos PostgreSQL especificada.
*   Creará un directorio temporal llamado `backup_data` dentro del directorio del script para almacenar los archivos CSV generados.
*   Para las tablas con la columna de fecha especificada, los datos se guardarán en subdirectorios `backup_data/YYYY/MM/DD/nombre_tabla.csv`.
*   Para las tablas sin columna de fecha, o si la columna no es utilizable, los datos se guardarán en `backup_data/nombre_tabla/nombre_tabla_part_N.csv`.
*   Una vez procesadas todas las tablas, el contenido del directorio `backup_data` se comprimirá en un archivo ZIP.
*   El archivo ZIP se guardará en el directorio `final_backups` (también creado dentro del directorio del script).
    El nombre del archivo ZIP seguirá el formato: `postgres_backup_[db_name]_[rango_fechas]_[timestamp].zip`.
*   Finalmente, el directorio temporal `backup_data` será eliminado.
