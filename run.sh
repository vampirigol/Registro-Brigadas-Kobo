#!/bin/bash
# Inicia el servidor web usando el entorno virtual
cd "$(dirname "$0")"
./venv/bin/python server.py
