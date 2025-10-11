#!/bin/bash
# Odiseo Bot Setup Script
# Installs dependencies and configures the environment

set -e  # Exit on error

echo "🚀 Odiseo Bot - Setup Script"
echo "=================================================="

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   ✅ Python $python_version"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -e .

# Check if .env exists
echo ""
if [ -f .env ]; then
    echo "✅ .env file already exists"
else
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your GOOGLE_API_KEY"
fi

# Make run script executable
echo ""
echo "🔧 Making run.sh executable..."
chmod +x run.sh

# Verify installation
echo ""
echo "🔍 Verifying system..."
python tools/verify_system.py

echo ""
echo "=================================================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your GOOGLE_API_KEY"
echo "  2. Run: ./run.sh"
echo ""
