#!/usr/bin/env bash
set -e

# Log python version and dependencies
python --version
pip freeze

# Run the main application
exec python -m streamlit run main_ui.py --server.port 8000