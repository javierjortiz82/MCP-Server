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

# Esperar a que MCP Server esté listo
echo "⏳ Esperando a que MCP Server esté listo..."
timeout=60
while [ $timeout -gt 0 ]; do
    if docker exec mcp-server curl -f http://localhost:8009/health > /dev/null 2>&1; then
        echo "✅ MCP Server está listo"
        break
    fi
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo "⚠️  MCP Server tardó pero continuando..."
fi

# Esperar a que Email Worker esté listo
echo "⏳ Esperando a que Email Worker esté listo..."
timeout=30
counter=0
while [ $counter -lt $timeout ]; do
    if docker ps --filter "name=mcp-email-worker" --filter "status=running" --quiet | grep -q .; then
        echo "✅ Email Worker está listo"
        break
    fi
    sleep 2
    counter=$((counter+2))
done

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
echo "🔌 MCP Server:"
echo "   • URL: http://localhost:8009"
echo "   • Health: http://localhost:8009/health"
echo ""
echo "📧 Email Worker:"
echo "   • Contenedor: mcp-email-worker"
echo "   • Estado: Procesando colas de email"
echo ""
echo "🔧 Comandos útiles:"
echo "   • Ver logs: docker-compose logs -f"
echo "   • Ver logs MCP: docker-compose logs -f mcp-server"
echo "   • Ver logs Email: docker-compose logs -f email-worker"
echo "   • Detener: docker-compose down"
echo "   • Estado: docker-compose ps"
echo "================================================"