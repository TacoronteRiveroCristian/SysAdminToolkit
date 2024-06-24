#!/bin/bash

# Variables de rutas
ZSH_CUSTOM_PATH="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"
ZSHRC_SOURCE_PATH="/path/to/source/.zshrc" # Cambia esta ruta al archivo .zshrc de origen

# Actualizar los paquetes e instalar Zsh si no está instalado
if ! command -v zsh >/dev/null 2>&1; then
    echo "Instalando Zsh..."
    sudo apt update && sudo apt install -y zsh
    chsh -s "$(which zsh)"
    # Forzar la recarga del shell
    exec zsh
else
    echo "Zsh ya está instalado."
fi

# Instalar Oh-My-Zsh si no está instalado
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    echo "Instalando Oh-My-Zsh..."
    sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
    OH_MY_ZSH_PID=$!
else
    echo "Oh-My-Zsh ya está instalado."
fi

# Instalar plugins y temas si no están instalados
if [ ! -d "${ZSH_CUSTOM_PATH}/plugins/zsh-autosuggestions" ]; then
    echo "Instalando plugin zsh-autosuggestions..."
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM_PATH}/plugins/zsh-autosuggestions
else
    echo "El plugin zsh-autosuggestions ya está instalado."
fi

if [ ! -d "${ZSH_CUSTOM_PATH}/plugins/zsh-syntax-highlighting" ]; then
    echo "Instalando plugin zsh-syntax-highlighting..."
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM_PATH}/plugins/zsh-syntax-highlighting
else
    echo "El plugin zsh-syntax-highlighting ya está instalado."
fi

# Instalar fzf si no está instalado
if ! command -v fzf >/dev/null 2>&1; then
    echo "Instalando fzf..."
    sudo apt install -y fzf
else
    echo "fzf ya está instalado."
fi

if [ ! -d "${ZSH_CUSTOM_PATH}/themes/powerlevel10k" ]; then
    echo "Instalando tema powerlevel10k..."
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM_PATH}/themes/powerlevel10k
else
    echo "El tema powerlevel10k ya está instalado."
fi

# Copiar el archivo .zshrc si existe en la ruta de origen
if [ -f "$ZSHRC_SOURCE_PATH" ]; then
    rm ~/.zshrc
    echo "Copiando archivo .zshrc..."
    cp "$ZSHRC_SOURCE_PATH" ~/.zshrc
else
    echo "Advertencia: No se encontró el archivo .zshrc en la ruta especificada."
fi

# Esperar a que Oh-My-Zsh termine de instalarse si se está ejecutando en segundo plano
if [ ! -z "$OH_MY_ZSH_PID" ]; then
    wait $OH_MY_ZSH_PID
fi

echo "Zsh instalado y configurado. Por favor, reinicie su sesión para ver los cambios (Con 'exit' o reiniciando el equipo o ususario)."

echo "Para personalizar la terminal con Powerlevel10k, ejecute el comando 'zsh' y siga las instrucciones de configuración."

echo "Para reiniciar su sesión, puede cerrar la sesión actual y volver a iniciarla, o puede reiniciar el equipo."
