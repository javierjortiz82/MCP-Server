#!/bin/bash
# Script para detener todos los servicios (PostgreSQL, pgAdmin, MCP Server, Email Worker)

echo "🛑 Deteniendo todos los servicios..."
echo "================================================"
echo "📋 Servicios a detener:"
echo "   • PostgreSQL (mcp-postgres)"
echo "   • pgAdmin (mcp-pgadmin)"
echo "   • MCP Server (mcp-server)"
echo "   • Email Worker (mcp-email-worker)"
echo ""

# Detener servicios
docker-compose down

echo "✅ Todos los servicios detenidos correctamente"
echo ""
echo "💡 Comandos útiles:"
echo "   • Para eliminar también los datos: docker-compose down -v"
echo "   • Ver servicios: docker-compose ps"
echo "   • Ver logs: docker-compose logs"
echo "================================================"