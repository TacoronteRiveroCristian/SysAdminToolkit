#!/bin/bash

# Detiene la ejecución si ocurre un error
set -e

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

# Pregunta al usuario si desea reiniciar
read -p "Es aconsejable reiniciar el equipo o la sesión, ¿desea reiniciar el equipo? (S/n) " respuesta

# Comprobar si la respuesta es 'S' o 's'
if [[ $respuesta =~ ^[Ss]$ ]]; then
    echo "Reiniciando el equipo..."
    sudo reboot
else
    echo "Reinicio cancelado. Por favor, reinicie el equipo o la sesión manualmente para aplicar los cambios."
fi
