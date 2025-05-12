# SysAdminToolkit

SysAdminToolkit es una colección de utilidades y scripts diseñados para facilitar las operaciones diarias de programadores y administradores de sistemas. Este repositorio contiene herramientas sencillas que permiten realizar tareas comunes de forma rápida y eficiente.

## Propósito

El objetivo principal de este proyecto es proporcionar soluciones simples para tareas repetitivas o complejas que los programadores y administradores enfrentan regularmente. Cada herramienta está diseñada para ser independiente y resolver un problema específico sin complicaciones.

## Uso

Cada submódulo en este repositorio funciona como un proyecto Git independiente. Puedes clonar el repositorio completo o solo los submódulos específicos que necesites:

```bash
# Clonar todo el repositorio
git clone https://github.com/username/SysAdminToolkit.git

# O clonar un submódulo específico
git clone https://github.com/username/SysAdminToolkit.git
cd SysAdminToolkit
git submodule update --init --recursive miscellaneous/backup_influxdb
```

## Herramientas disponibles

### backup_influxdb

Herramienta para crear backups entre instancias de InfluxDB, permitiendo filtrar y transferir datos selectivamente.

#### Casos de uso prácticos

1. **Backup completo de base de datos**

   Para respaldar todas las mediciones y todos los campos de una base de datos a otra instancia:

   ```yaml
   source:
     url: http://produccion-influxdb:8086
     databases:
       - name: telegraf
         destination: telegraf_backup
     user: "admin"
     password: "password123"

   destination:
     url: http://backup-influxdb:8086
     user: "backup"
     password: "secure456"

   measurements:
     include: []  # Vacío = incluir todas las mediciones
     exclude: []
     specific: {}  # Sin configuración específica = incluir todos los campos
   ```

2. **Respaldo selectivo de mediciones críticas**

   Para respaldar solo mediciones específicas del sistema:

   ```yaml
   measurements:
     include: [cpu, memory, disk, system]  # Solo estas mediciones
     exclude: []
     specific: {}  # Sin filtrado adicional de campos
   ```

3. **Filtrado avanzado de datos**

   Para respaldar solo campos específicos de alto valor y excluir datos temporales:

   ```yaml
   measurements:
     include: []  # Todas las mediciones
     exclude: [temporary_data, debug_metrics]  # Excluir estas
     specific:
       cpu:
         fields:
           include: [usage_system, usage_user, usage_idle]  # Solo estos campos
           types: [numeric]  # Solo valores numéricos

       disk:
         fields:
           include: [used_percent, free]  # Solo campos de espacio relevantes
           types: [numeric]
   ```

4. **Respaldo programado automatizado**

   Para configurar un respaldo que ocurra cada día a medianoche:

   ```yaml
   options:
     backup_schedule: "0 0 * * *"
     log_level: INFO
     log_file: /var/log/backup_influxdb/backup.log
   ```

#### Ejecución

Para ejecutar un respaldo:

```bash
cd docker/backup_influxdb
# Copiar y personalizar la configuración
cp backup_config.yaml.template backup_config.yaml
# Editar según necesidades
nano backup_config.yaml
# Ejecutar respaldo
docker-compose up -d
```

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request para mejorar este proyecto. Si quieres añadir una nueva utilidad, asegúrate de seguir la estructura del repositorio y documentar adecuadamente su funcionamiento.

## Licencia

Ver archivo [LICENSE](LICENSE) para más detalles.
