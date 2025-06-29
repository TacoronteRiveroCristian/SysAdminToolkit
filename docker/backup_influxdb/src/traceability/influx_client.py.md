# Trazabilidad del Script: `influx_client.py`

*Este documento sigue la evolución del script `influx_client.py`, registrando los cambios significativos, decisiones de diseño y correcciones a lo largo del tiempo.*

---

### Actualización - 2024-07-29

**Cambios Realizados:**
- Se ha añadido un nuevo método `get_databases()` a la clase `InfluxClient`.

**Justificación:**
- Este método es un requisito para implementar la funcionalidad de "respaldar todas las bases de datos" en `backup.py`. Permite al gestor de backups obtener dinámicamente la lista de todas las bases de datos disponibles en el servidor de origen cuando el usuario no las especifica en la configuración.

**Consideraciones y Riesgos:**
- La correcta ejecución de este método depende de que el usuario/token configurado para la conexión con InfluxDB tenga los permisos necesarios para listar bases de datos. Si no los tiene, la operación fallará.

**Errores Corregidos:**
- N/A (Nueva funcionalidad).

---
