"""Entry points called by the worker: ``boot()`` once, ``run_user_code()`` per run."""
from __future__ import annotations

import base64
import builtins
import importlib.abc
import io
import json
import linecache
import os
import sys
import sysconfig
import traceback

from . import host

ROOT = "/hivebr"  # tests override this with a temporary copy of the repo layout
_LIB_MARKERS = ("site-packages", "dist-packages", ".zip")
_SKIP_DIRS = {"src", "web", "__pycache__", ".git", "node_modules"}


def user_dir() -> str:
    """Folder where the worker writes the editor tabs (entry script + modules)."""
    return os.path.join(ROOT, "user_scripts")


def boot():
    """Make the runtime importable (only adds missing paths) and patch the engine."""
    for p in (os.path.join(ROOT, "web"), os.path.join(ROOT, "src"), ROOT):
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    from . import simulator
    simulator.install()
    simulator.reset_editor()


# ------------------------------------------------------------- editor ----
def ensure_editor():
    """Simulator used by the UI while no script is running."""
    from . import simulator
    return simulator.ensure_editor(os.path.join(ROOT, "config", "default.yaml"))


def dispatch_edit(raw):
    """Apply one UI command to the idle editor (there is no execution loop)."""
    from . import commands, simulator
    sim = simulator.editor() or ensure_editor()
    commands.dispatch(sim, raw, editing=True)
    sim._emit()
    return None


def reset_edits():
    """Discard every UI edit and rebuild the idle editor from the client config.

    The next run then starts from the scene defined by the user's script
    (the run file), without re-applying obstacles, waypoints, maps or poses
    added through the canvas.
    """
    from . import edits, simulator
    edits.reset()
    simulator.reset_editor()
    ensure_editor()
    return None


def script_path(filename: str | None = None) -> str:
    """Entry script path. With ``filename`` the script lives beside its modules."""
    if not filename:
        return os.path.join(ROOT, "examples", "user_script.py")
    name = os.path.basename(str(filename).replace("\\", "/")).strip() or "user_script.py"
    if not name.endswith(".py"):
        name += ".py"
    return os.path.join(user_dir(), name)


# --------------------------------------------------------------- files ----
def _snapshot():
    snap = {}
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for n in names:
            if n.endswith(".pyc"):
                continue
            p = os.path.join(base, n)
            try:
                st = os.stat(p)
            except OSError:
                continue
            snap[p] = (st.st_size, st.st_mtime_ns)
    return snap


def _changed_files(before):
    return [{"path": p, "size": v[0]} for p, v in sorted(_snapshot().items()) if before.get(p) != v]


# ------------------------------------------------------------- modules ----
def _lib_roots():
    paths = {sysconfig.get_path(k) for k in ("stdlib", "platstdlib", "purelib", "platlib")}
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # directory holding hivebr_web
    paths.add(here)
    try:
        import hivebr
        paths.add(os.path.dirname(os.path.dirname(os.path.abspath(hivebr.__file__))))
    except Exception:
        pass
    return tuple(os.path.realpath(p) for p in paths if p)


def _module_paths(mod):
    f = getattr(mod, "__file__", None)
    if f:
        return [f]
    try:
        return list(getattr(mod, "__path__", ()))
    except Exception:
        return []


def _under(path, base):
    path, base = os.path.realpath(path), os.path.realpath(base)
    return path == base or path.startswith(base + os.sep)


def _purge_user_modules(before):
    """Drop example/template/user modules so the next run imports them afresh."""
    user_dirs = [os.path.join(ROOT, "examples"), os.path.join(ROOT, "templates"), user_dir()]
    libs = _lib_roots()
    for name, mod in list(sys.modules.items()):
        paths = _module_paths(mod)
        if not paths:
            continue
        in_user_dir = any(_under(p, d) for p in paths for d in user_dirs)
        is_library = any(m in p for p in paths for m in _LIB_MARKERS) or any(_under(p, b) for p in paths for b in libs)
        if in_user_dir or (name not in before and not is_library):
            sys.modules.pop(name, None)


# ---------------------------------------------------------- matplotlib ----
class _MplHook(importlib.abc.MetaPathFinder):
    """Patches matplotlib.pyplot right after the user script imports it."""

    def find_spec(self, name, path=None, target=None):
        if name != "matplotlib.pyplot":
            return None
        for finder in sys.meta_path:
            if finder is self or not hasattr(finder, "find_spec"):
                continue
            spec = finder.find_spec(name, path, target)
            if spec is not None and spec.loader is not None and hasattr(spec.loader, "exec_module"):
                loader = spec.loader
                original = loader.exec_module

                def exec_module(module, _orig=original):
                    _orig(module)
                    _patch_pyplot(module)

                loader.exec_module = exec_module
                return spec
        return None


def _patch_pyplot(plt):
    if getattr(plt, "_hivebr_patched", False):
        return
    try:
        plt.switch_backend("Agg")
    except Exception:
        pass

    def show(*args, **kwargs):
        for num in plt.get_fignums():
            fig = plt.figure(num)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            host.post("figure", {"title": _fig_title(fig, num),
                                 "png_b64": base64.b64encode(buf.getvalue()).decode("ascii")})
        plt.close("all")

    plt.show = show
    plt._hivebr_patched = True


def _fig_title(fig, num):
    sup = getattr(fig, "_suptitle", None)
    if sup is not None and sup.get_text():
        return sup.get_text()
    for ax in fig.axes:
        if ax.get_title():
            return ax.get_title()
    return f"Figure {num}"


def _prepare_matplotlib():
    os.environ["MPLBACKEND"] = "Agg"
    if not any(isinstance(f, _MplHook) for f in sys.meta_path):
        sys.meta_path.insert(0, _MplHook())
    if "matplotlib.pyplot" in sys.modules:
        _patch_pyplot(sys.modules["matplotlib.pyplot"])


def _close_figures():
    plt = sys.modules.get("matplotlib.pyplot")
    if plt is not None:
        try:
            plt.close("all")
        except Exception:
            pass


# ----------------------------------------------------------------- run ----
def _error_report(exc, script):
    tb = exc.__traceback__
    while tb is not None and tb.tb_frame.f_code.co_filename == __file__:
        tb = tb.tb_next
    line = getattr(exc, "lineno", None) if isinstance(exc, SyntaxError) else None
    walk = tb
    while walk is not None:
        if walk.tb_frame.f_code.co_filename == script:
            line = walk.tb_lineno
        walk = walk.tb_next
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, tb)),
        "line": line,
    }


def run_user_code(code: str, autostart: bool = False, filename: str | None = None) -> str:
    """Execute ``code`` as ``__main__`` and return the ``finished`` payload as JSON.

    ``filename`` selects the entry script inside the user scripts folder; its
    siblings are importable, so the editor can hold several modules.
    """
    from . import simulator

    script = script_path(filename)
    os.makedirs(os.path.dirname(script), exist_ok=True)
    linecache.cache[script] = (len(code), None, code.splitlines(True), script)
    saved = (sys.argv, list(sys.path), os.getcwd())
    modules_before = set(sys.modules)
    files_before = _snapshot()
    result = {"ok": True, "stopped": False, "error": None}

    simulator.autostart = bool(autostart)
    _prepare_matplotlib()
    sys.argv = ["user_script.py"]
    sys.path.insert(0, os.path.dirname(script))  # like running the file: siblings are importable
    os.chdir(ROOT)
    namespace = {"__name__": "__main__", "__file__": script, "__builtins__": builtins,
                 "__doc__": None, "__package__": None, "__spec__": None, "__loader__": None}
    try:
        exec(compile(code, script, "exec"), namespace)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        result["stopped"] = True
    except BaseException as exc:
        result["ok"] = False
        result["error"] = _error_report(exc, script)
    finally:
        simulator.autostart = False
        _close_figures()
        sys.argv = saved[0]
        sys.path[:] = saved[1]
        os.chdir(saved[2])
        _purge_user_modules(modules_before)
        try:
            simulator.enter_edit_mode()
        except Exception as exc:  # never hide the run result behind an editor error
            traceback.print_exc()
            host.notice("warn", f"Could not return to edit mode: {exc!r}", "edit_mode_failed", error=repr(exc))
    result["files"] = _changed_files(files_before)
    return json.dumps(result)
