#!/bin/bash
# Script para iniciar PostgreSQL + pgAdmin para MCP

echo "🚀 Iniciando PostgreSQL + pgAdmin para MCP..."
echo "================================================"

# Verificar que Docker esté disponible
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado o no está en PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado o no está en PATH"
    exit 1
fi

# Iniciar servicios
echo "📦 Iniciando servicios..."
docker-compose up -d

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a que PostgreSQL esté listo..."
timeout=60
while [ $timeout -gt 0 ]; do
    if docker exec mcp-postgres pg_isready -U mcp_user -d mcpdb > /dev/null 2>&1; then
        echo "✅ PostgreSQL está listo"
        break
    fi
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo "❌ Timeout esperando PostgreSQL"
    exit 1
fi

echo ""
echo "🎉 Servicios iniciados correctamente!"
echo "================================================"
echo "📊 PostgreSQL:"
echo "   • Host: localhost"
echo "   • Puerto: 5434"
echo "   • Base de datos: mcpdb"
echo "   • Usuario: mcp_user"
echo "   • Contraseña: mcp_password"
echo ""
echo "🖥️  pgAdmin:"
echo "   • URL: http://localhost:8090"
echo "   • Email: admin@example.com"
echo "   • Contraseña: admin123"
echo ""
echo "🔧 Comandos útiles:"
echo "   • Ver logs: docker-compose logs -f"
echo "   • Detener: docker-compose down"
echo "   • Estado: docker-compose ps"
echo "================================================"