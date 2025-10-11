#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "Poblando DB con products.json..."
python3 "$ROOT_DIR/src/populate-db.py"
echo "Población finalizada."
