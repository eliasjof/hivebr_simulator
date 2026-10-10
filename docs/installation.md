# Installation

## Requirements

- Python **3.8+**
- A desktop environment (the engine opens a Pygame window)

## From source (recommended)

```bash
git clone https://github.com/eliasjof/hivebr_simulator.git
cd hivebr_simulator

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e .
```

The package uses a `src/` layout, so `pip install -e .` is the easiest way to
make `import hivebr` resolve everywhere. If you prefer not to install, add the
source folder to your path:

=== "Windows (PowerShell)"

    ```powershell
    $env:PYTHONPATH = "src"
    ```

=== "Linux / macOS"

    ```bash
    export PYTHONPATH=src
    ```

## Dependencies

`hivebr` depends on:

| Package      | Version     | Purpose                          |
| ------------ | ----------- | -------------------------------- |
| `pygame-ce`  | `>=2.5.0`   | Rendering and event loop         |
| `pygame_gui` | `>=0.6.9`   | Interactive control panel        |
| `numpy`      | `>=1.24`    | Vector math                      |
| `PyYAML`     | `>=6.0`     | Configuration files              |

Optional extras used by some examples and by occupancy-grid maps:

- `Pillow` and `scipy` (image loading and binary dilation for map inflation).
- `matplotlib` (data logger plots).
- `ompl` (only for the OMPL planner adapter).

## Building the documentation

The docs are built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)
and [mkdocstrings](https://mkdocstrings.github.io/).

```bash
pip install -r requirements-docs.txt
mkdocs serve     # live preview at http://127.0.0.1:8000
mkdocs build     # static site into ./site
```

## Publishing to GitHub Pages

The `.github/workflows/DeployDocs.yml` workflow builds the site and pushes it to
the `gh-pages` branch on every push to `main`.

!!! info "One-time setup"
    In **Settings → Pages**, set the source to the **`gh-pages`** branch (root).
    The site is then available at
    <https://eliasjof.github.io/hivebr_simulator/>.

To preview locally:

```bash
mkdocs serve
```
