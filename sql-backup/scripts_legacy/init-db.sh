#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "Inicializando DB (script Python)..."
python3 "$ROOT_DIR/src/init-db.py"
echo "Inicialización finalizada."
