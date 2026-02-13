#!/usr/bin/env bash
set -e

# Log python version and dependencies
python --version
pip freeze

# Run the main application for Azure App Service
exec python -m streamlit run main_ui.py --server.port 8000 --server.address 0.0.0.0