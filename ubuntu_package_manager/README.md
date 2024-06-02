# Ubuntu Package Manager

Este submódulo es parte del repositorio [SysAdminToolkit](https://github.com/tu-usuario/SysAdminToolkit) y contiene scripts para la instalación de paquetes en sistemas basados en Ubuntu.

## Contenido

- **docker**: Contiene el script `install_docker.sh` para instalar Docker y Docker Compose en Ubuntu.
- **code-server**: Configuración para ejecutar code-server con Docker Compose.
- **ohmyzsh**: Script `install_zsh.sh` para instalar y configurar Oh My Zsh.

## Scripts de Instalación

### Docker y Docker Compose

El script `install_docker.sh` se utiliza para instalar Docker y Docker Compose en un sistema Ubuntu. Este script:

- Actualiza los paquetes del sistema.
- Elimina cualquier versión conflictiva de Docker.
- Configura el repositorio oficial de Docker.
- Instala Docker CE, Docker CLI, y Docker Compose.
- Añade el usuario actual al grupo Docker para poder ejecutar comandos Docker sin `sudo`.

#### Uso

Para ejecutar el script, abre una terminal y ejecuta los siguientes comandos:

```bash
cd docker
chmod +x install_docker.sh
./install_docker.sh
```

### Code Server

El directorio code-server contiene una configuración para ejecutar code-server utilizando Docker Compose.

- `docker-compose.yaml`: Archivo de configuración de Docker Compose.
- `Dockerfiles/code-server.Dockerfile`: Dockerfile para construir la imagen de code-server.
- `volumes/codeserver/project`: Directorio de ejemplo para almacenar proyectos en code-server.

#### Uso

Para iniciar code-server, navega al directorio code-server y ejecuta Docker Compose:

```bash
cd code-server
docker-compose up -d
```

### Oh My Zsh

El script install_zsh.sh instala Zsh y configura Oh My Zsh que es una herramienta que permite agregar funciones avanzadas a la terminal de Ubuntu y personalizarla.

#### Uso

Para ejecutar el script, abre una terminal y ejecuta los siguientes comandos:

```bash
cd ohmyzsh
chmod +x install_zsh.sh
./install_zsh.sh
```
