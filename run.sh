#!/usr/bin/env bash
set -euo pipefail

# Print structure (Debug)
echo "Working dir: $(pwd)"
echo "Listing:"
ls -la

# Entrypoint
TARGET="main_ui.py"

if [ ! -f "$TARGET" ]; then
  echo "ERROR: $TARGET not found in folder: $(pwd)"
  exit 1
fi

exec python -m streamlit run "$TARGET" --server.port 8000 --server.address 0.0.0.0