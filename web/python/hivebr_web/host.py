"""Bridge to the JS worker. The host object is installed by ``set_host``.

Host interface: ``post(type, json_str)``, ``poll() -> str | None``,
``sleep(ms)`` (returns early when a command arrives) and ``now() -> ms``.
"""
from __future__ import annotations

import json
import time

_host = None


class _DetachedHost:
    """Used when no host is installed (plain Python): nothing is delivered."""

    def post(self, type, payload): pass
    def poll(self): return None
    def sleep(self, ms): time.sleep(max(0.0, ms) / 1000.0)
    def now(self): return time.perf_counter() * 1000.0


def set_host(obj) -> None:
    global _host
    _host = obj


def get_host():
    return _host if _host is not None else _DetachedHost()


def post(type: str, payload) -> None:
    """Serialize ``payload`` as strict JSON and send it to the UI."""
    get_host().post(type, dumps(payload))


def dumps(obj) -> str:
    return json.dumps(obj, allow_nan=False, separators=(",", ":"), default=_default)


def _default(o):
    if hasattr(o, "tolist"):
        return o.tolist()
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(f"not serializable: {type(o).__name__}")


def notice(level: str, text: str) -> None:
    post("notice", {"level": level, "text": str(text)})
