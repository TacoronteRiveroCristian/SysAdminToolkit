#!/bin/bash

# Detiene la ejecución si ocurre un error
set -e

# Función para instalar Docker y Docker Compose
install_docker() {
    # Actualiza los paquetes e instala las dependencias necesarias
    sudo apt-get update

    # Elimina paquetes conflictivos
    for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
        sudo apt-get remove -y $pkg || true
    done

    # Elimina la configuración de paquetes anteriores
    if [ -f "/etc/apt/sources.list.d/docker.list" ]; then
        sudo rm /etc/apt/sources.list.d/docker.list
    fi

    # Añadir clave GPG oficial de Docker:
    sudo apt-get install -y ca-certificates curl gnupg-agent software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

    # Añadir el repositorio apt:
    sudo add-apt-repository \
       "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
       $(lsb_release -cs) \
       stable"

    sudo apt-get update

    # Instalar la última versión de Docker y sus componentes
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Permite que tu usuario ejecute comandos Docker sin sudo (cambia $USER por tu nombre de usuario si es necesario)
    sudo usermod -aG docker $USER

    # Instala Docker Compose
    sudo apt-get install -y docker-compose

    # Muestra la versión de Docker y Docker Compose para confirmar la instalación
    docker --version
    docker-compose --version

    echo "Instalación de Docker y Docker Compose completada."
}

# Función para desinstalar Docker y Docker Compose
uninstall_docker() {
    # Mostrar un mensaje de confirmación antes de proceder
    read -p "¿Está seguro de que desea desinstalar Docker y Docker Compose y limpiar el sistema? (S/n) " confirmacion

    # Comprobar si la respuesta es 'S' o 's'
    if [[ ! $confirmacion =~ ^[Ss]$ ]]; then
        echo "Desinstalación cancelada."
        exit 1
    fi

    # Eliminar Docker y sus componentes
    for pkg in docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-compose; do
        sudo apt-get remove --purge -y $pkg
    done

    # Eliminar las dependencias que ya no son necesarias
    sudo apt-get autoremove -y
    sudo apt-get autoclean

    # Eliminar archivos de configuración y directorios de Docker
    sudo rm -rf /var/lib/docker
    sudo rm -rf /etc/docker
    sudo rm -rf /var/run/docker.sock

    # Eliminar los repositorios y claves de Docker
    if [ -f "/etc/apt/sources.list.d/docker.list" ]; then
        sudo rm /etc/apt/sources.list.d/docker.list
    fi

    if [ -f "/etc/apt/keyrings/docker.asc" ]; then
        sudo rm /etc/apt/keyrings/docker.asc
    fi

    # Eliminar grupo docker
    sudo groupdel docker || true

    # Actualizar la lista de paquetes
    sudo apt-get update

    # Verificar que Docker y Docker Compose se han desinstalado correctamente
    if ! command -v docker &> /dev/null && ! command -v docker-compose &> /dev/null; then
        echo "Docker y Docker Compose se han desinstalado y limpiado correctamente."
    else
        echo "Ocurrió un error al desinstalar Docker y Docker Compose."
    fi
}

# Verificar el argumento pasado al script
if [ "$1" == "install" ]; then
    install_docker
elif [ "$1" == "uninstall" ]; then
    uninstall_docker
else
    echo "Uso: $0 {install|uninstall}"
    exit 1
fi

# Pregunta al usuario si desea reiniciar
read -p "Es aconsejable reiniciar el equipo o la sesión, ¿desea reiniciar el equipo? (S/n) " respuesta

# Comprobar si la respuesta es 'S' o 's'
if [[ $respuesta =~ ^[Ss]$ ]]; then
    echo "Reiniciando el equipo..."
    sudo reboot
else
    echo "Reinicio cancelado. Por favor, reinicie el equipo o la sesión manualmente para aplicar los cambios."
fi
