#!/bin/bash
# Installation script for Client MCP (Odiseo Bot)

set -e  # Exit on error

echo "🚀 Installing Client MCP Dependencies..."
echo "========================================="

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if (( $(echo "$PYTHON_VERSION < $REQUIRED_VERSION" | bc -l) )); then
    echo "❌ Error: Python $REQUIRED_VERSION+ required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"

# Install from requirements.txt (parent directory)
if [ -f "../requirements.txt" ]; then
    echo ""
    echo "📦 Installing from requirements.txt..."
    pip install -r ../requirements.txt
else
    echo ""
    echo "📦 Installing from pyproject.toml..."
    pip install -e .
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Copy .env.example to .env"
echo "  2. Add your GOOGLE_API_KEY to .env"
echo "  3. Run: python -m client_mcp"
