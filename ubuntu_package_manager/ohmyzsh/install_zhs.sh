#!/bin/bash

# Variables de rutas
ZSH_CUSTOM_PATH="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"

# Actualizar los paquetes e instalar Zsh si no está instalado
if ! command -v zsh >/dev/null 2>&1; then
    echo "Instalando Zsh..."
    sudo apt update && sudo apt install -y zsh
    chsh -s "$(which zsh)"
else
    echo "Zsh ya está instalado."
fi

# Instalar Oh-My-Zsh si no está instalado
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    echo "Instalando Oh-My-Zsh..."
    sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
else
    echo "Oh-My-Zsh ya está instalado."
fi

# Instalar plugins y temas
echo "Instalando plugins y temas..."
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM_PATH}/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM_PATH}/plugins/zsh-syntax-highlighting

# Instalar fzf si no está instalado
if ! command -v fzf >/dev/null 2>&1; then
    echo "Instalando fzf..."
    sudo apt install fzf
else
    echo "fzf ya está instalado."
fi

# Copiar el archivo .zshrc si existe
if [ -f ".zshrc" ]; then
    cp .zshrc ~/.zshrc
else
    echo "Advertencia: No se encontró el archivo .zshrc para copiar."
fi

git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM_PATH}/themes/powerlevel10k

echo "Zsh instalado y configurado. Por favor, reinicie su sesión para ver los cambios."

