# Portainer - Gestión de Contenedores Docker

Portainer es una herramienta de gestión de contenedores Docker con interfaz web que te permite visualizar y administrar todos tus contenedores, imágenes, redes y volúmenes de manera organizada.

## 🚀 Inicio Rápido

### Prerrequisitos
- Docker instalado y ejecutándose
- Docker Compose instalado

### Instalación y Ejecución

1. **Navegar al directorio de Portainer:**
   ```bash
   cd docker/portainer
   ```

2. **Levantar el servicio:**
   ```bash
   docker-compose up -d
   ```

3. **Verificar que está funcionando:**
   ```bash
   docker-compose ps
   ```

## 🌐 Acceso a la Interfaz Web

Una vez que el contenedor esté ejecutándose, puedes acceder a Portainer en:

- **HTTP:** http://localhost:9000
- **HTTPS:** https://localhost:9443

### Primera Configuración

1. La primera vez que accedas, te pedirá crear un usuario administrador
2. Configura tu usuario y contraseña
3. Selecciona "Docker" como entorno local
4. ¡Ya puedes gestionar todos tus contenedores!

## ⚙️ Configuración

### Puertos Utilizados

- **9000:** Interfaz web HTTP
- **9443:** Interfaz web HTTPS

### Volúmenes

- **portainer_data:** Almacena la configuración y datos de Portainer
- **/var/run/docker.sock:** Socket de Docker (solo lectura) para comunicarse con el daemon

### Características Principales

- ✅ Gestión visual de contenedores
- ✅ Monitoring en tiempo real
- ✅ Gestión de imágenes y volúmenes
- ✅ Configuración de redes
- ✅ Logs de contenedores
- ✅ Estadísticas de uso
- ✅ Plantillas de aplicaciones

## 🔧 Comandos Útiles

```bash
# Iniciar Portainer
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar Portainer
docker-compose down

# Actualizar a la última versión
docker-compose pull
docker-compose up -d

# Backup de datos de Portainer
docker run --rm -v portainer_portainer_data:/data -v $(pwd):/backup alpine tar czf /backup/portainer_backup.tar.gz -C /data .

# Restaurar backup
docker run --rm -v portainer_portainer_data:/data -v $(pwd):/backup alpine tar xzf /backup/portainer_backup.tar.gz -C /data
```

## 🔒 Seguridad

- El socket de Docker está montado en modo solo lectura
- Portainer corre con políticas de reinicio automático
- Red aislada para el contenedor
- Acceso tanto HTTP como HTTPS disponible

## 🔄 Actualización

Para actualizar Portainer a la última versión:

```bash
docker-compose down
docker-compose pull
docker-compose up -d
```

## 📊 Monitoreo

Portainer te permitirá:

- Ver todos los contenedores del sistema
- Monitorear uso de CPU y memoria
- Gestionar redes Docker
- Administrar volúmenes
- Ver logs en tiempo real
- Ejecutar comandos en contenedores
- Gestionar stacks de Docker Compose

## 🆘 Solución de Problemas

### Puerto ocupado
Si el puerto 9000 está ocupado:
```bash
# Modificar el puerto en docker-compose.yml
ports:
  - "9001:9000"  # Usar puerto 9001 en lugar de 9000
```

### Problemas de permisos
```bash
# Asegurar que Docker esté ejecutándose
sudo systemctl status docker

# Verificar permisos del usuario
sudo usermod -aG docker $USER
```

### Logs del contenedor
```bash
docker-compose logs portainer
```

¡Con esta configuración tendrás una vista completa y organizada de todos tus contenedores Docker!
