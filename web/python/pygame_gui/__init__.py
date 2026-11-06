"""Headless pygame_gui stand-in: every widget is an inert catch-all object."""
import sys
import types

from pygame import _NULL, _fallback

# Distinct event ids so comparisons against pygame event types stay meaningful.
UI_BUTTON_PRESSED = 33000
UI_HORIZONTAL_SLIDER_MOVED = 33001
UI_TEXT_ENTRY_FINISHED = 33002
UI_TEXT_ENTRY_CHANGED = 33003
UI_FILE_DIALOG_PATH_PICKED = 33004
UI_WINDOW_CLOSE = 33005
UI_DROP_DOWN_MENU_CHANGED = 33006
UI_CONFIRMATION_DIALOG_CONFIRMED = 33007

for _sub in ("elements", "windows", "core", "data", "ui_manager"):
    _mod = types.ModuleType(f"{__name__}.{_sub}")
    _mod.__getattr__ = _fallback
    sys.modules[_mod.__name__] = _mod
    globals()[_sub] = _mod

__getattr__ = _fallback
UIManager = _NULL
