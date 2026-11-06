"""Headless tkinter stand-in (file dialogs and windows are inert)."""
import sys
import types

from pygame import _NULL, _fallback

for _sub in ("filedialog", "messagebox", "ttk", "simpledialog"):
    _mod = types.ModuleType(f"{__name__}.{_sub}")
    _mod.__getattr__ = _fallback
    sys.modules[_mod.__name__] = _mod
    globals()[_sub] = _mod

Tk = _NULL
TclError = type("TclError", (Exception,), {})
__getattr__ = _fallback
