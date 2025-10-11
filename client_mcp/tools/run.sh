#!/bin/bash
# Odiseo Bot Launcher Script
# Sets up the environment and runs the bot

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set PYTHONPATH to include client_mcp directory (portable)
export PYTHONPATH="${SCRIPT_DIR}:$PYTHONPATH"

# Change to script directory
cd "$SCRIPT_DIR"

# Run the bot
python __main__.py
