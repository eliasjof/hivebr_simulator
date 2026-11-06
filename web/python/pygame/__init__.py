"""Headless pygame stand-in used when hivebr runs in the browser.

Nothing is rendered. Anything not implemented explicitly resolves to a
catch-all ``_Null`` object, so code written against pygame keeps importing and
running. ``pygame.draw.*`` calls aimed at the active recorder surface are
captured, which lets ``draw_callback`` overlays reach the web canvas.
"""
from __future__ import annotations

import sys
import time as _time
import types as _types

__version__ = "2.6.0-web"


class _Null:
    """Callable, falsy, inert object: every attribute and operation yields itself."""

    __slots__ = ()

    def __call__(self, *a, **k): return self
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return self
    def __iter__(self): return iter(())
    def __len__(self): return 0
    def __bool__(self): return False
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __index__(self): return 0
    def __getitem__(self, key): return self
    def __setitem__(self, key, value): pass
    def __contains__(self, item): return False
    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def __repr__(self): return "<pygame null>"
    __hash__ = object.__hash__
    def __eq__(self, other): return False
    def __ne__(self, other): return True
    def __lt__(self, other): return False
    def __le__(self, other): return False
    def __gt__(self, other): return False
    def __ge__(self, other): return False


def _ident(self, *a): return self


for _op in ("add", "sub", "mul", "truediv", "floordiv", "mod", "pow", "matmul",
            "and", "or", "xor", "lshift", "rshift"):
    setattr(_Null, f"__{_op}__", _ident)
    setattr(_Null, f"__r{_op}__", _ident)
for _op in ("neg", "pos", "abs", "invert"):
    setattr(_Null, f"__{_op}__", lambda self: self)

_NULL = _Null()


class error(Exception):
    pass


# --- constants (values match pygame 2) -------------------------------------
QUIT, ACTIVEEVENT, KEYDOWN, KEYUP = 256, 32768, 768, 769
MOUSEMOTION, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEWHEEL = 1024, 1025, 1026, 1027
VIDEORESIZE, VIDEOEXPOSE, USEREVENT, NOEVENT = 32769, 32770, 32847, 0
KMOD_NONE, KMOD_LSHIFT, KMOD_RSHIFT, KMOD_SHIFT = 0, 1, 2, 3
KMOD_LCTRL, KMOD_RCTRL, KMOD_CTRL = 64, 128, 192
KMOD_LALT, KMOD_RALT, KMOD_ALT = 256, 512, 768
SRCALPHA, RESIZABLE, FULLSCREEN, DOUBLEBUF = 0x00010000, 16, -2147483648, 0x40000000
HWSURFACE, OPENGL, NOFRAME, SCALED, ANYFORMAT = 1, 2, 32, 0x200, 0x10000000
BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT = 1, 2, 3
BLEND_ADD, BLEND_SUB, BLEND_MULT, BLEND_RGBA_ADD = 1, 2, 3, 6

_KEYS = {
    "BACKSPACE": 8, "TAB": 9, "RETURN": 13, "ESCAPE": 27, "SPACE": 32, "DELETE": 127,
    "UP": 1073741906, "DOWN": 1073741905, "LEFT": 1073741904, "RIGHT": 1073741903,
    "LSHIFT": 1073742049, "RSHIFT": 1073742053, "LCTRL": 1073742048, "RCTRL": 1073742052,
    "LALT": 1073742050, "RALT": 1073742054, "HOME": 1073741898, "END": 1073741901,
    "PAGEUP": 1073741899, "PAGEDOWN": 1073741902, "INSERT": 1073741897,
    "PLUS": 43, "MINUS": 45, "EQUALS": 61, "COMMA": 44, "PERIOD": 46, "SLASH": 47,
}
for _n, _v in _KEYS.items():
    globals()[f"K_{_n}"] = _v
for _i in range(26):
    globals()[f"K_{chr(97 + _i)}"] = 97 + _i
for _i in range(10):
    globals()[f"K_{_i}"] = 48 + _i
for _i in range(1, 13):
    globals()[f"K_F{_i}"] = 1073741881 + _i


# --- geometry / color ------------------------------------------------------
class Rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, *args):
        if len(args) == 1:
            args = tuple(args[0])
        if len(args) == 2:
            (self.x, self.y), (self.w, self.h) = args
        elif len(args) == 4:
            self.x, self.y, self.w, self.h = args
        else:
            self.x = self.y = self.w = self.h = 0

    width = property(lambda s: s.w, lambda s, v: setattr(s, "w", v))
    height = property(lambda s: s.h, lambda s, v: setattr(s, "h", v))
    left = property(lambda s: s.x, lambda s, v: setattr(s, "x", v))
    top = property(lambda s: s.y, lambda s, v: setattr(s, "y", v))
    right = property(lambda s: s.x + s.w, lambda s, v: setattr(s, "x", v - s.w))
    bottom = property(lambda s: s.y + s.h, lambda s, v: setattr(s, "y", v - s.h))
    centerx = property(lambda s: s.x + s.w / 2, lambda s, v: setattr(s, "x", v - s.w / 2))
    centery = property(lambda s: s.y + s.h / 2, lambda s, v: setattr(s, "y", v - s.h / 2))
    size = property(lambda s: (s.w, s.h))
    topleft = property(lambda s: (s.x, s.y))
    center = property(lambda s: (s.x + s.w / 2, s.y + s.h / 2))

    @center.setter
    def center(self, v): self.centerx, self.centery = v

    @topleft.setter
    def topleft(self, v): self.x, self.y = v

    @size.setter
    def size(self, v): self.w, self.h = v

    def copy(self): return Rect(self.x, self.y, self.w, self.h)
    def move(self, dx, dy): return Rect(self.x + dx, self.y + dy, self.w, self.h)
    def move_ip(self, dx, dy): self.x += dx; self.y += dy
    def inflate(self, dw, dh): return Rect(self.x - dw / 2, self.y - dh / 2, self.w + dw, self.h + dh)
    def collidepoint(self, *p):
        px, py = p[0] if len(p) == 1 else p
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h
    def colliderect(self, o):
        o = Rect(o)
        return self.x < o.x + o.w and o.x < self.x + self.w and self.y < o.y + o.h and o.y < self.y + self.h
    def __iter__(self): return iter((self.x, self.y, self.w, self.h))
    def __len__(self): return 4
    def __getitem__(self, i): return (self.x, self.y, self.w, self.h)[i]
    def __eq__(self, o):
        try: return tuple(self) == tuple(Rect(o))
        except Exception: return False
    __hash__ = None
    def __repr__(self): return f"<rect({self.x}, {self.y}, {self.w}, {self.h})>"


class Color(tuple):
    def __new__(cls, *args):
        if len(args) == 1 and not isinstance(args[0], (int, float)):
            args = tuple(args[0]) if not isinstance(args[0], str) else (0, 0, 0)
        if len(args) == 1:
            v = int(args[0]); args = ((v >> 16) & 255, (v >> 8) & 255, v & 255)
        vals = [int(c) for c in args][:4]
        while len(vals) < 4:
            vals.append(255)
        return super().__new__(cls, vals)

    r = property(lambda s: s[0])
    g = property(lambda s: s[1])
    b = property(lambda s: s[2])
    a = property(lambda s: s[3])


class _Vector2:
    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=None):
        if y is None:
            x, y = x if hasattr(x, "__iter__") else (x, x)
        self.x, self.y = float(x), float(y)

    def __iter__(self): return iter((self.x, self.y))
    def __getitem__(self, i): return (self.x, self.y)[i]
    def __len__(self): return 2
    def __add__(self, o): return _Vector2(self.x + o[0], self.y + o[1])
    __radd__ = __add__
    def __sub__(self, o): return _Vector2(self.x - o[0], self.y - o[1])
    def __rsub__(self, o): return _Vector2(o[0] - self.x, o[1] - self.y)
    def __mul__(self, k):
        return self.x * k[0] + self.y * k[1] if hasattr(k, "__iter__") else _Vector2(self.x * k, self.y * k)
    __rmul__ = __mul__
    def __truediv__(self, k): return _Vector2(self.x / k, self.y / k)
    def __neg__(self): return _Vector2(-self.x, -self.y)
    def __eq__(self, o): return tuple(self) == tuple(o)
    def length(self): return (self.x ** 2 + self.y ** 2) ** 0.5
    def length_squared(self): return self.x ** 2 + self.y ** 2
    def dot(self, o): return self.x * o[0] + self.y * o[1]
    def normalize(self):
        n = self.length()
        return _Vector2(self.x / n, self.y / n) if n else _Vector2()
    def distance_to(self, o): return (self - o).length()
    def __repr__(self): return f"<Vector2({self.x}, {self.y})>"


# --- Surface ----------------------------------------------------------------
class Surface(_Null):
    """Pixel-less surface: only remembers its size."""

    __slots__ = ("_size",)

    def __init__(self, size=(0, 0), flags=0, *a, **k):
        try:
            self._size = (int(size[0]), int(size[1]))
        except Exception:
            self._size = (0, 0)

    def get_size(self): return self._size
    def get_width(self): return self._size[0]
    def get_height(self): return self._size[1]
    def get_rect(self, **k):
        r = Rect(0, 0, *self._size)
        for key, val in k.items():
            setattr(r, key, val)
        return r
    def convert(self, *a): return self
    def convert_alpha(self, *a): return self
    def copy(self): return Surface(self._size)
    def subsurface(self, *a): return self
    def blit(self, *a, **k): return Rect(0, 0, 0, 0)
    def fill(self, *a, **k): return Rect(0, 0, *self._size)
    def __bool__(self): return True
    def __eq__(self, other): return self is other
    def __ne__(self, other): return self is not other
    __hash__ = object.__hash__
    def __repr__(self): return f"<Surface({self._size[0]}x{self._size[1]})>"


# --- draw recorder ----------------------------------------------------------
class _Recorder:
    def __init__(self, screen):
        self.screen = screen
        self.items = []


_recorder = None


def _begin_record(screen):
    global _recorder
    _recorder = _Recorder(screen)


def _end_record():
    """Stop recording; returns ``[(kind, color, points, width_or_radius, extra)]``."""
    global _recorder
    items = _recorder.items if _recorder else []
    _recorder = None
    return items


def _rec(surface, kind, color, pts, size):
    r = _recorder
    if r is not None and surface is r.screen:
        r.items.append((kind, color, pts, size))
    return Rect(0, 0, 0, 0)


def _pt(p):
    return (float(p[0]), float(p[1]))


def _line(surface, color, start, end, width=1):
    return _rec(surface, "line", color, [_pt(start), _pt(end)], width)

def _lines(surface, color, closed, points, width=1):
    pts = [_pt(p) for p in points]
    if closed and pts:
        pts.append(pts[0])
    return _rec(surface, "line", color, pts, width) if len(pts) > 1 else Rect()

def _circle(surface, color, center, radius, width=0, *a, **k):
    return _rec(surface, "circle", color, [_pt(center)], (float(radius), width))

def _polygon(surface, color, points, width=0):
    return _rec(surface, "poly", color, [_pt(p) for p in points], width)

def _rect(surface, color, rect, width=0, *a, **k):
    x, y, w, h = Rect(rect)
    return _rec(surface, "poly", color, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], width)


# --- submodules ---------------------------------------------------------------
def _fallback(name):
    if name.startswith("__"):
        raise AttributeError(name)
    return _NULL


def _module(_name, **attrs):
    mod = _types.ModuleType(f"{__name__}.{_name}")
    mod.__dict__.update(attrs)
    mod.__dict__["__getattr__"] = _fallback
    sys.modules[mod.__name__] = mod
    globals()[_name] = mod
    return mod


class _Clock:
    def __init__(self):
        self._last = _time.perf_counter()
        self._ms = 0
        self._fps = 0.0

    def tick(self, framerate=0):
        now = _time.perf_counter()
        self._ms = int((now - self._last) * 1000)
        self._last = now
        if self._ms > 0:
            self._fps = 0.9 * self._fps + 0.1 * (1000.0 / self._ms) if self._fps else 1000.0 / self._ms
        return self._ms

    tick_busy_loop = tick
    def get_fps(self): return float(self._fps)
    def get_time(self): return self._ms
    def get_rawtime(self): return self._ms


_module("time", Clock=_Clock,
        get_ticks=lambda: int(_time.perf_counter() * 1000),
        wait=lambda ms: int(ms), delay=lambda ms: int(ms),
        set_timer=lambda *a, **k: None)

_state = {"screen": None, "caption": ("pygame", "pygame")}


def _set_mode(size=(0, 0), flags=0, *a, **k):
    _state["screen"] = Surface(size, flags)
    return _state["screen"]


class _VideoInfo:
    current_w, current_h = 1400, 800


_module("display", init=lambda: None, quit=lambda: None, get_init=lambda: True,
        set_mode=_set_mode, get_surface=lambda: _state["screen"],
        set_caption=lambda title, icon=None: None, get_caption=lambda: _state["caption"],
        set_icon=lambda s: None, flip=lambda: None, update=lambda *a: None,
        Info=_VideoInfo, get_window_size=lambda: (_state["screen"] or Surface()).get_size(),
        toggle_fullscreen=lambda: 0)

_module("event", get=lambda *a, **k: [], poll=lambda: None, pump=lambda: None,
        clear=lambda *a: None, post=lambda e: True, wait=lambda *a: None,
        Event=lambda type, **k: _types.SimpleNamespace(type=type, **k),
        set_allowed=lambda *a: None, peek=lambda *a: False)

_module("mouse", get_pos=lambda: (0, 0), get_pressed=lambda *a, **k: (False, False, False),
        get_rel=lambda: (0, 0), set_visible=lambda v: True, set_pos=lambda *a: None,
        get_focused=lambda: False)


class _KeyState:
    def __getitem__(self, k): return False
    def __iter__(self): return iter(())
    def __len__(self): return 0


_module("key", get_pressed=lambda: _KeyState(), get_mods=lambda: 0, get_focused=lambda: False,
        name=lambda k: "", set_repeat=lambda *a: None)

_module("draw", line=_line, aaline=_line, lines=_lines, aalines=_lines, circle=_circle,
        polygon=_polygon, rect=_rect,
        ellipse=lambda s, c, r, w=0, *a, **k: Rect(r), arc=lambda *a, **k: Rect())


class _Font:
    def __init__(self, name=None, size=20, *a, **k):
        self.size_px = int(size or 20)

    def size(self, text): return (int(len(str(text)) * self.size_px * 0.55), self.size_px)
    def render(self, text, aa=True, color=(255, 255, 255), bg=None):
        return Surface(self.size(text))
    def get_linesize(self): return int(self.size_px * 1.2)
    def get_height(self): return self.size_px
    def get_ascent(self): return int(self.size_px * 0.8)
    def get_descent(self): return -int(self.size_px * 0.2)
    def set_bold(self, v): pass
    def set_italic(self, v): pass
    def set_underline(self, v): pass


_module("font", init=lambda: None, quit=lambda: None, get_init=lambda: True,
        Font=_Font, SysFont=lambda name=None, size=20, *a, **k: _Font(name, size),
        match_font=lambda *a, **k: None, get_fonts=lambda: [], get_default_font=lambda: "default")

_module("image", load=lambda *a, **k: Surface((1, 1)),
        frombuffer=lambda buf, size, fmt="RGB", *a: Surface(size),
        fromstring=lambda buf, size, fmt="RGB", *a: Surface(size),
        tostring=lambda s, fmt="RGB", *a: bytes([255]) * (s.get_width() * s.get_height() * len(fmt)),
        tobytes=lambda s, fmt="RGB", *a: bytes([255]) * (s.get_width() * s.get_height() * len(fmt)),
        save=lambda *a, **k: None)

_module("transform",
        scale=lambda s, size, *a, **k: Surface(size), smoothscale=lambda s, size, *a, **k: Surface(size),
        flip=lambda s, *a: s, rotate=lambda s, *a: s, rotozoom=lambda s, *a: s,
        scale_by=lambda s, f, *a, **k: s)
_module("surfarray")
_module("mixer", init=lambda *a, **k: None, quit=lambda: None, get_init=lambda: False)
_module("math", Vector2=_Vector2, Vector3=_Vector2)
_module("locals")
_module("mask")
_module("sprite")
_module("joystick", init=lambda: None, get_count=lambda: 0)

# `pygame.locals` mirrors the constants defined above.
locals.__dict__.update({k: v for k, v in globals().items() if k.isupper() or k.startswith(("K_", "KMOD_"))})
locals.__dict__.update(Rect=Rect, Color=Color)

Vector2 = _Vector2
init = lambda: (5, 0)
quit = lambda: None
get_init = lambda: True
get_error = lambda: ""


__getattr__ = _fallback
