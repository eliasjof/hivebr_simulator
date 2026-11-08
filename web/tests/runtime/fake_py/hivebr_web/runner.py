"""Stand-in for the real runner, used only when web/python is not available."""
import json, sys, traceback
from . import host


def boot():
    pass


def _loop():
    h = host.get_host()
    h.post("scene", json.dumps({"version": 1, "robots": [{"id": 0}]}))
    t = 0.0
    step = 0
    running = True
    speed = 1.0
    last = h.now()
    while True:
        while True:
            raw = h.poll()
            if raw is None:
                break
            c = json.loads(raw)
            if c["cmd"] == "stop":
                return
            if c["cmd"] == "pause":
                running = False
            if c["cmd"] == "start":
                running = True
            if c["cmd"] == "set_speed":
                speed = c["factor"]
        if running:
            t += 0.03 * speed
            step += 1
        now = h.now()
        if now - last >= 16:
            last = now
            h.post("frame", json.dumps({"t": t, "step": step, "running": running, "speed": speed, "robots": [{"id": 0}]}))
        h.sleep(5)


def run_user_code(code, autostart, filename=None):
    g = {"__name__": "__main__", "fake_run": _loop}
    err = None
    stopped = False
    try:
        exec(compile(code, "user_script.py", "exec"), g)
    except KeyboardInterrupt:
        stopped = True
        err = {"type": "KeyboardInterrupt", "message": "", "traceback": "", "line": None}
    except BaseException as e:
        err = {"type": type(e).__name__, "message": str(e), "traceback": traceback.format_exc(), "line": None}
    return json.dumps({"ok": err is None, "stopped": stopped, "error": err, "files": []})
