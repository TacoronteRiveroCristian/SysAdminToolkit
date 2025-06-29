# Trazabilidad del Script: `backup.py`

*Este documento sigue la evolución del script `backup.py`, registrando los cambios significativos, decisiones de diseño y correcciones a lo largo del tiempo.*

---

### Actualización - 2024-07-29

**Cambios Realizados:**
- Se ha modificado el método `_process_databases` para implementar una nueva lógica de selección de bases de datos.
- Si la lista `source.databases` de la configuración está vacía, el script ahora obtiene automáticamente todas las bases de datos del servidor de origen, excluyendo la base de datos interna `_internal`.
- Se ha añadido soporte para los campos de configuración `source.prefix` y `source.suffix`. Estos se aplican a los nombres de las bases de datos de destino para facilitar su identificación y evitar colisiones de nombres.

**Justificación:**
- El objetivo es aumentar la flexibilidad y facilidad de uso del script. Permite a los usuarios realizar un backup completo de un servidor InfluxDB sin necesidad de listar explícitamente cada base de datos. Los prefijos y sufijos ofrecen una manera de organizar mejor los datos en el servidor de destino.

**Consideraciones y Riesgos:**
- **Riesgo de backup masivo:** Si un usuario deja la lista de bases de datos vacía por error, podría iniciar un backup de gran volumen no deseado, lo que podría consumir una cantidad significativa de red y almacenamiento.
- **Nombres de BBDD:** La concatenación de prefijo, nombre original y sufijo podría, en casos extremos, generar nombres de bases de datos demasiado largos o con caracteres no válidos para InfluxDB.

**Errores Corregidos:**
- N/A (Nueva funcionalidad).

---
