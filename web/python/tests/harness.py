"""Shared helpers: fake host, temporary repo layout, run_user_code wrapper."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY_DIR = HERE.parent                       # web/python
REPO = PY_DIR.parent.parent                # repository root

for p in (str(REPO), str(REPO / "src"), str(PY_DIR)):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)


def _reject(token):
    raise ValueError(f"non-strict JSON constant: {token}")


class FakeHost:
    """Scripted stand-in for the JS worker. Time is simulated, sleep is free."""

    def __init__(self):
        self.t = 0.0
        self.commands = deque()
        self.posts = []                      # (type, payload)
        self.sleeps = []
        self.frame_hooks = []                # callables(frame_index, frame, host)
        self.poll_hook = None
        self.frames = 0

    # --- host interface ---
    def post(self, type, payload):
        data = json.loads(payload, parse_constant=_reject)   # strict JSON check
        self.posts.append((type, data))
        if type == "frame":
            self.frames += 1
            for hook in list(self.frame_hooks):
                hook(self.frames, data, self)

    def poll(self):
        if self.poll_hook:
            self.poll_hook(self)
        return self.commands.popleft() if self.commands else None

    def sleep(self, ms):
        self.sleeps.append(ms)
        if not self.commands:
            self.t += max(0.0, ms)

    def now(self):
        self.t += 0.02
        return self.t

    # --- scripting helpers ---
    def send(self, **cmd):
        self.commands.append(json.dumps(cmd))

    def after_frames(self, n, **cmd):
        def hook(i, frame, host, done=[False]):
            if i >= n and not done[0]:
                done[0] = True
                host.send(**cmd)
        self.frame_hooks.append(hook)

    def of(self, type):
        return [p for t, p in self.posts if t == type]

    def notices(self, level=None):
        return [n for n in self.of("notice") if level is None or n["level"] == level]


def make_root(tmp: Path | None = None) -> Path:
    """Temporary copy of the repo layout: src (link), config and examples (copies)."""
    root = Path(tmp or tempfile.mkdtemp(prefix="hivebr_root_"))
    (root / "src").symlink_to(REPO / "src", target_is_directory=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pkl")
    shutil.copytree(REPO / "config", root / "config", ignore=ignore)
    shutil.copytree(REPO / "examples", root / "examples", ignore=ignore)
    (root / "templates").mkdir()
    return root


class Env:
    """Installed runtime + fake host + temporary root."""

    def __init__(self):
        import hivebr.engine  # noqa: F401  (load from the repo, not from the temporary root)
        from hivebr_web import host as host_mod, runner
        self.host = FakeHost()
        host_mod.set_host(self.host)
        self.root = make_root()
        runner.ROOT = str(self.root)
        self._cwd = os.getcwd()
        os.chdir(self.root)          # like the worker: relative paths resolve inside the root
        runner.boot()
        self.runner = runner

    def run(self, code, autostart=False, capture=True):
        out = io.StringIO()
        ctx = contextlib.redirect_stdout(out) if capture else contextlib.nullcontext()
        with ctx:
            raw = self.runner.run_user_code(code, autostart)
        self.stdout = out.getvalue()
        return json.loads(raw)

    def run_example(self, name, **kw):
        return self.run((REPO / "examples" / name).read_text(encoding="utf-8"), **kw)

    def close(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.root, ignore_errors=True)
        from hivebr_web import host as host_mod
        host_mod.set_host(None)


def positions(frame):
    return [(r["x"], r["y"]) for r in frame["robots"]]


def moved(host):
    """Largest displacement of any robot between the first and last frame."""
    frames = host.of("frame")
    a, b = positions(frames[0]), positions(frames[-1])
    return max(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 for p, q in zip(a, b))


@contextlib.contextmanager
def env(**kw):
    e = Env()
    try:
        yield e
    finally:
        e.close()


def run_for(e, code, frames=60, start=True, **kw):
    """Run ``code``; send ``start`` immediately and ``stop`` after ``frames`` frames."""
    if start:
        e.host.send(cmd="start")
    e.host.after_frames(frames, cmd="stop")
    return e.run(code, **kw)


def check(cond, msg="assertion failed"):
    if not cond:
        raise AssertionError(msg)
