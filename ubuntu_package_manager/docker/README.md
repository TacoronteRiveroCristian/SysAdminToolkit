# Instalador Docker y Docker Compose

Para instalar o desisntalar Docker y Docker Compose en una máquina Ubuntu cuya versión puede ser la 22.04 o 18.04 LTS puede hacerse mediante los ficheros que se encuentran en este apartado.

Su uso es simple:

1. Dar permisos necesarios al fichero correspondiente: `sudo chmod +x file.sh`.
2. Ejecutar mediante el comando `install` o `uninstall` si se desea instalar o desinstalar respectivamente.

Por ejemplo, si se desea instalar Docker y Docker Compose en una máquina, se debe de ejecutar el siguiente comando:
```bash
sudo chmod +x ./install_docker_v2204LTS.sh
./install_docker_v2204LTS.sh install
```