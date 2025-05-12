# SysAdminToolkit

SysAdminToolkit es una colección de utilidades y scripts diseñados para facilitar las operaciones diarias de programadores y administradores de sistemas. Este repositorio funciona como una biblioteca de herramientas reutilizables que cualquier programador puede incorporar fácilmente en su flujo de trabajo.

## Propósito

El objetivo principal de este proyecto es proporcionar soluciones simples y reutilizables para tareas repetitivas o complejas que los programadores y administradores enfrentan regularmente. Cada herramienta está diseñada para:

- Resolver un problema específico sin complicaciones
- Ser independiente y fácil de integrar
- Ahorrar tiempo al evitar "reinventar la rueda"
- Servir como ejemplo práctico de implementación

## Uso

Cada submódulo en este repositorio funciona como un componente independiente. Puedes clonar solo la utilidad específica que necesitas sin tener que descargar todo el repositorio:

```bash
# Clonar todo el repositorio
git clone https://github.com/username/SysAdminToolkit.git

# Clonar solo un directorio/utilidad específica (usando sparse-checkout)
mkdir SysAdminToolkit
cd SysAdminToolkit
git init
git remote add origin https://github.com/username/SysAdminToolkit.git
git config core.sparseCheckout true
echo "docker/backup_influxdb" >> .git/info/sparse-checkout  # Reemplazar con la ruta deseada
git pull origin main
```

## Herramientas disponibles

### Docker

#### backup_influxdb
Herramienta para crear backups entre instancias de InfluxDB, permitiendo filtrar y transferir datos selectivamente.

**Uso**: Navega a `docker/backup_influxdb`, personaliza el archivo de configuración y ejecuta con Docker Compose.

#### host_monitoring
Sistema de monitorización para hosts usando Prometheus y Grafana.

**Uso**: Navega a `docker/host_monitoring` y sigue las instrucciones en el README local.

### Linux

#### code-server
Configuración para desplegar VS Code en un servidor remoto mediante contenedores.

**Uso**: Consulta los Dockerfiles en `linux/code-server/Dockerfiles` y ajusta según tus necesidades.

#### docker
Scripts y utilidades para gestionar contenedores Docker en entornos Linux.

#### ohmyzsh
Configuraciones y plugins personalizados para Oh My Zsh.

### Miscellaneous

#### backup_influxdb
Versión alternativa de la herramienta de backup para InfluxDB.

#### check_ping
Herramienta para monitorizar conectividad de red y reportar a Telegraf/InfluxDB.

**Uso**: Configura los archivos en `miscellaneous/check_ping/volumes/telegraf` y despliega usando Docker.

#### email_sender
Utilidad simple para enviar correos electrónicos programados o basados en eventos.

#### setup_python_project
Script para configurar rápidamente la estructura de un nuevo proyecto Python con buenas prácticas.



## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request para mejorar este proyecto. Si quieres añadir una nueva utilidad:

1. Crea un directorio con un nombre descriptivo
2. Incluye un README.md explicando el propósito y uso de la herramienta
3. Organiza el código de manera que sea fácil de entender y reutilizar
4. Agrega ejemplos de uso cuando sea posible

## Licencia

Ver archivo [LICENSE](LICENSE) para más detalles.
