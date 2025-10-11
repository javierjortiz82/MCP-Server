#!/bin/bash
# Script para detener PostgreSQL + pgAdmin

echo "🛑 Deteniendo servicios PostgreSQL + pgAdmin..."
echo "================================================"

# Detener servicios
docker-compose down

echo "✅ Servicios detenidos correctamente"
echo ""
echo "💡 Para eliminar también los datos:"
echo "   docker-compose down -v"