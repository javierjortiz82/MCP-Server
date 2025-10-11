#!/bin/bash
# Run script for Client MCP (Odiseo Bot)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🤖 Starting Odiseo Bot..."
echo "========================"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "   Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env and add your GOOGLE_API_KEY${NC}"
        exit 1
    else
        echo -e "${RED}❌ Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Check if GOOGLE_API_KEY is set
if ! grep -q "GOOGLE_API_KEY=.*[a-zA-Z0-9]" .env; then
    echo -e "${RED}❌ Error: GOOGLE_API_KEY not set in .env${NC}"
    echo "   Please edit .env and add your API key"
    exit 1
fi

echo -e "${GREEN}✅ Configuration validated${NC}"
echo ""

# Run from parent directory to use module execution
cd ..
python -m client_mcp
