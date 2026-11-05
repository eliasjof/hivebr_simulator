# Pyodide Build for hivebr-web

This directory contains the Pyodide build configuration for running the real hivebr simulation engine in the browser via WebAssembly.

## Prerequisites

- Python 3.10+
- pip
- pyodide-build (`pip install pyodide-build`)
- hivebr package installed (`pip install -e ../../../`)

## Building

### 1. Build hivebr wheel
```bash
cd ../../../
pip install -e .
pip wheel . -w dist/
```

### 2. Build Pyodide package
```bash
cd web/pyodide
pip install pyodide-build
pyodide-build --wheel ../../../dist/hivebr-*.whl
```

Output will be in `./dist/`

### 3. Copy to frontend
```bash
cp -r dist/* ../frontend/public/pyodide/
```

## Development

For development, you can use the mock worker (already implemented in `web/frontend/src/worker/simulator.worker.ts`) which simulates the physics in JavaScript.

To switch to Pyodide:
1. Build the Pyodide packages
2. Update `SimulatorWorker.ts` to use the Pyodide worker
3. Copy Pyodide runtime to `web/frontend/public/pyodide/`

## Files

- `pyproject.toml` - Pyodide build configuration
- `web_simulator.py` - Python WebSimulator using real hivebr.engine.core
- `pyodide_worker.js` - Worker entry point that loads Pyodide
- `build_pyodide.sh` - Build script

## Pyodide Packages

The following packages are included:
- `numpy` - Numerical computations
- `scipy` - Scientific computing (for occupancy grid dilation)
- `pyyaml` - YAML config parsing
- `hivebr-web-core` - Our simulator core (built from source)

## Pyodide Version

Using Pyodide 0.25.1 (Python 3.12)

## CDN

Pyodide is loaded from CDN at runtime:
```
https://cdn.jsdelivr.net/pyodide/v0.25.1/full/
```

For production, consider hosting Pyodide locally.