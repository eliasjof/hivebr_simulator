#!/bin/bash
# build_pyodide.sh - Build Pyodide packages for hivebr-web

set -e

echo "Building hivebr-web-core for Pyodide..."

# Build the hivebr package first
cd /path/to/hivebr_simulator
pip install -e .
pip wheel . -w dist/

# Build Pyodide package
cd web/pyodide
pip install pyodide-build

# Build with the local hivebr wheel
pyodide-build --wheel ../../dist/hivebr-*.whl

echo "Pyodide build complete! Output in ./dist/"