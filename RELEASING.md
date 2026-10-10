# Releasing hivebr

This project publishes to [PyPI](https://pypi.org/project/hivebr/) as `hivebr`.

## 1. Bump the version

Edit `version` in `pyproject.toml` (semantic versioning, e.g. `0.1.1`, `0.2.0`).
Keep `hivebr.__version__` in `src/hivebr/__init__.py` in sync.

## 2. Build locally and check the metadata

```bash
python -m pip install -U build twine
python -m build
python -m twine check dist/*
```

`python -m build` produces:

- `dist/hivebr-<version>.tar.gz` (sdist)
- `dist/hivebr-<version>-py3-none-any.whl` (wheel)

Inspect the wheel to confirm the engine assets and subpackages are present:

```bash
python -m zipfile -l dist/hivebr-*.whl
```

## 3. Test the wheel in a clean environment

```bash
python -m venv /tmp/hivebr-test
# Windows: /tmp/hivebr-test/Scripts/activate ; Linux/macOS:
source /tmp/hivebr-test/bin/activate
pip install dist/hivebr-*.whl
python -c "import hivebr; print(hivebr.__version__)"
python -c "from hivebr.engine import Simulator; print('engine ok')"
```

## 4. Publish

### Option A — Automated (recommended, Trusted Publishing)

Pushing a GitHub **release** (or running the `Publish to PyPI` workflow
manually) triggers `.github/workflows/Publish.yml`, which builds and uploads the
distributions.

One-time setup on PyPI:

1. Go to **PyPI → Your projects → Publishing** (or
   <https://pypi.org/manage/account/publishing/>).
2. Add a **pending publisher** / trusted publisher with:
   - PyPI project name: `hivebr`
   - Owner: `eliasjof`
   - Repository: `hivebr_simulator`
   - Workflow name: `Publish.yml`
   - Environment name: `pypi`
3. Create a GitHub **environment** named `pypi` (Settings → Environments).

No API token is required.

### Option B — Manual

```bash
python -m twine upload dist/*
```

Use an API token (`__token__` as username) when prompted, or set `TWINE_USERNAME`
and `TWINE_PASSWORD` (or a `~/.pypirc`) beforehand.

## 5. Tag the release

```bash
git tag v0.1.1
git push origin v0.1.1
```

## Checklist

- [ ] Version bumped in `pyproject.toml` and `src/hivebr/__init__.py`
- [ ] `python -m build` succeeds
- [ ] `python -m twine check dist/*` passes
- [ ] Wheel imports fine in a clean venv
- [ ] Docs build (`mkdocs build --strict`)
- [ ] GitHub release created (triggers the publish workflow)
