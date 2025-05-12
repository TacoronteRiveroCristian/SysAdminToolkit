FROM codercom/code-server:latest

USER root

# Instalar sudo
RUN apt-get update && apt-get install -y sudo python3-pip

# Cambiar de nuevo al usuario no privilegiado
USER coder

# Instalar dependencias
COPY ./volumes/codeserver/project/env/requirements.txt /home/codeserver/project/env/requirements.txt
WORKDIR /home/codeserver/project/env
RUN pip install --no-cache-dir -r requirements.txt

# Instalar la extensiones (deben ejecutarse por separado las extensiones)
RUN code-server --install-extension ms-python.python
RUN code-server --install-extension njpwerner.autodocstring
RUN code-server --install-extension ms-toolsai.jupyter

# Copiar el archivo de configuración a la carpeta de configuración de Code Server
COPY ./volumes/codeserver/project/env/settings.json /home/coder/.local/share/code-server/User/settings.json

WORKDIR /home/coder/project
