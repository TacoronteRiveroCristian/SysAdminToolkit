#!/bin/bash

# Script de inicio rápido para Portainer
# Gestión de contenedores Docker con interfaz web

echo "🐳 Iniciando Portainer - Gestión de Contenedores Docker"
echo "=================================================="

# Verificar si Docker está ejecutándose
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está ejecutándose o no tienes permisos"
    echo "💡 Intenta: sudo systemctl start docker"
    echo "💡 O agregar tu usuario al grupo docker: sudo usermod -aG docker $USER"
    exit 1
fi

# Verificar si Docker Compose está disponible
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose no está instalado"
    echo "💡 Instala Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Navegar al directorio del script
cd "$(dirname "$0")"

echo "🚀 Levantando Portainer..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ¡Portainer se ha iniciado correctamente!"
    echo ""
    echo "🌐 Accede a la interfaz web en:"
    echo "   • HTTP:  http://localhost:9000"
    echo "   • HTTPS: https://localhost:9443"
    echo ""
    echo "📋 Primera vez:"
    echo "   1. Crea tu usuario administrador"
    echo "   2. Selecciona 'Docker' como entorno local"
    echo "   3. ¡Disfruta gestionando tus contenedores!"
    echo ""
    echo "🔧 Comandos útiles:"
    echo "   • Ver estado: docker-compose ps"
    echo "   • Ver logs:   docker-compose logs -f"
    echo "   • Parar:      docker-compose down"
    echo ""
else
    echo "❌ Error al iniciar Portainer"
    echo "🔍 Revisa los logs con: docker-compose logs"
    exit 1
fi
