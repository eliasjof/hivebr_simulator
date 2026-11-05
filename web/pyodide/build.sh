#!/bin/bash
# Build script for Pyodide/WASM
# Run this in a Pyodide environment (or use pyodide-build)

set -e

echo "Building hivebr-web-core for Pyodide..."

# Option 1: Using pyodide-build (recommended)
if command -v pyodide-build &> /dev/null; then
    echo "Using pyodide-build..."
    cd "$(dirname "$0")"
    pyodide-build --wheel ../../../dist/hivebr-*.whl
    echo "Build complete! Output in ./dist/"
else
    echo "pyodide-build not found. Install with: pip install pyodide-build"
    echo "Or run this inside the Pyodide Docker image."
fi

# Option 2: Manual build with emscripten (for reference)
# emcc -o hivebr.wasm ...

echo "Done!"