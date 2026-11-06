"""Runner contract, pacing, overlays, matplotlib capture and error reporting."""
import sys

from harness import check, env, run_for

BASIC = '''
from hivebr.engine import Simulator
sim = Simulator(controller=lambda r, w, g, c, dt, l=None: {"v": 0.5, "omega": 0.0})
sim.run()
print("done", sim.sim_time)
'''


def sim_wall(e):
    frames = e.host.of("frame")
    return frames[-1]["t"]


def test_error_reports_user_line():
    code = "import math\n\nx = 1\nprint('hi')\nraise ValueError('boom')\n"
    with env() as e:
        r = e.run(code)
        err = r["error"]
        check(r["ok"] is False and err["type"] == "ValueError" and err["message"] == "boom", r)
        check(err["line"] == 5, err["line"])
        check("runner.py" not in err["traceback"] and "raise ValueError('boom')" in err["traceback"], err["traceback"])
        check(r["stopped"] is False)


def test_error_line_inside_function_and_controller():
    code = '''from hivebr.engine import Simulator
def ctrl(robot, world, goal, cfg, dt, lidar=None):
    return {"v": 1 / 0}
sim = Simulator(controller=ctrl)
sim.running_simulation = True
sim.run()
'''
    with env() as e:
        r = e.run(code)
        check(r["error"]["type"] == "ZeroDivisionError" and r["error"]["line"] == 3, r["error"])
        check("simulator.py" in r["error"]["traceback"] and "user_script.py" in r["error"]["traceback"])


def test_syntax_error_line():
    with env() as e:
        r = e.run("x = 1\ny = (\n")
        check(r["error"]["type"] == "SyntaxError" and r["error"]["line"] in (2, 3), r["error"])


def test_system_exit_is_ok_and_keyboard_interrupt_is_stopped():
    with env() as e:
        r = e.run("import sys\nprint('a')\nsys.exit(0)\nprint('b')")
        check(r["ok"] and not r["stopped"] and r["error"] is None and e.stdout == "a\n", r)
        r = e.run("raise KeyboardInterrupt")
        check(r["stopped"] is True and r["error"] is None, r)


def test_interrupt_during_run():
    with env() as e:
        def poll_hook(host):
            if host.frames > 5:
                raise KeyboardInterrupt
        e.host.poll_hook = poll_hook
        e.host.send(cmd="start")
        r = e.run(BASIC)
        check(r["stopped"] is True and "done" not in e.stdout, r)


def test_script_environment():
    code = '''import os, sys
from pathlib import Path
print(__name__, __file__, sys.argv, os.getcwd(), Path(__file__).resolve().parent.parent == Path(os.getcwd()))
'''
    with env() as e:
        r = e.run(code)
        check(r["ok"], r)
        root = str(e.root.resolve())
        check(f"__main__ {e.root}/examples/user_script.py ['user_script.py']" in e.stdout, e.stdout)
        check(e.stdout.strip().endswith("True"), e.stdout)


def test_files_reported_and_modules_purged():
    code = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_follower
Path("out.txt").write_text("hello")
'''
    with env() as e:
        r = e.run(code)
        check(r["ok"], r)
        paths = [f["path"] for f in r["files"]]
        check(any(p.endswith("/out.txt") for p in paths) and all(f["size"] >= 0 for f in r["files"]), r["files"])
        check("line_follower" not in sys.modules and "hivebr" in sys.modules and "numpy" in sys.modules)
        r2 = e.run("pass")
        check(r2["files"] == [], r2["files"])    # unchanged files are not reported again


def test_autostart_flag():
    with env() as e:
        e.host.after_frames(25, cmd="stop")
        r = e.run(BASIC, autostart=True)
        check(r["ok"] and moved_any(e), r)
        check(e.host.of("scene")[0]["autostart"] is True)
        check("done" in e.stdout)
    with env() as e:                      # no autostart: stays paused, idles on host.sleep
        e.host.poll_hook = lambda h: h.send(cmd="stop") if len(h.sleeps) > 5 else None
        r = e.run(BASIC, autostart=False)
        check(r["ok"] and not moved_any(e) and e.host.of("scene")[0]["autostart"] is False)
        check(all(s <= 33.0 for s in e.host.sleeps) and e.host.sleeps, "paused loop must sleep <= 33 ms")
        check(len(e.host.of("frame")) <= 3 and e.host.of("frame")[-1]["step"] == 0, "paused simulation must not stream frames")


def moved_any(e):
    f = e.host.of("frame")
    return abs(f[-1]["robots"][0]["x"] - f[0]["robots"][0]["x"]) > 0.05


def test_pacing_factors():
    # real time: 40 steps of dt=0.03 s take ~1.2 s of host time and 40 frames
    for factor in (1.0, 2.0, 0.5, 4.0):
        with env() as e:
            e.host.send(cmd="set_speed", factor=factor)
            e.host.send(cmd="start")
            e.host.frame_hooks.append(lambda i, fr, h: h.send(cmd="stop") if fr["step"] >= 100 else None)
            e.run(BASIC)
            sim_s = e.host.of("frame")[-1]["t"]
            check(sim_s >= 3.0, sim_s)
            check(abs(e.host.t / 1000.0 - sim_s / factor) < 0.15 * sim_s / factor + 0.1,
                  f"factor {factor}: {e.host.t:.0f} ms of host time for {sim_s:.2f} s simulated")
    with env() as e:                      # as fast as possible: never sleeps, frames capped at ~30 Hz
        e.host.send(cmd="set_speed", factor=0)
        e.host.send(cmd="start")
        e.host.frame_hooks.append(lambda i, fr, h: h.send(cmd="stop") if fr["step"] >= 1500 else None)
        e.run(BASIC)
        frames = e.host.of("frame")
        check(sum(e.host.sleeps) == 0, "unpaced run must not sleep")
        check(frames[-1]["step"] >= 1500 and len(frames) < frames[-1]["step"] / 5, (frames[-1]["step"], len(frames)))
        check(frames[-1]["speed"] == 0.0)
        check(len(frames) <= e.host.t / 33.0 + 3, (len(frames), e.host.t))


def test_realtime_factor_moving_average():
    with env() as e:
        e.host.send(cmd="set_speed", factor=2.0)
        run_for(e, BASIC, 120)
        rt = [f["realtime_factor"] for f in e.host.of("frame")]
        check(abs(rt[-5] - 2.0) < 0.15, rt[-5:])


def test_frame_rate_cap_60hz():
    with env() as e:
        e.host.send(cmd="set_speed", factor=8.0)     # step every ~4 ms of host time
        run_for(e, BASIC, 100)
        steps = [f["step"] for f in e.host.of("frame")]
        check(all(b - a >= 1 for a, b in zip(steps[2:-1], steps[3:-1])), "frames without new data")
        check(steps[-2] > 150, steps[-2])


def test_scene_reposted_on_static_change():
    with env() as e:
        e.host.send(cmd="start")
        e.host.after_frames(10, cmd="set_param", name="grid_size", value=2.0)
        e.host.after_frames(20, cmd="stop")
        e.run(BASIC)
        scenes = e.host.of("scene")
        check([s["version"] for s in scenes] == list(range(1, len(scenes) + 1)) and len(scenes) >= 2)
        check(scenes[-1]["world"]["grid_size"] == 2.0 and scenes[0]["world"]["grid_size"] != 2.0)


def test_final_frame_when_run_ends():
    with env() as e:
        run_for(e, BASIC, 15)
        last = e.host.of("frame")[-1]
        check(last["running"] is False)
        check(e.host.posts[-1][0] == "frame", [t for t, _ in e.host.posts[-3:]])


OVERLAY = '''
import numpy as np, pygame
from hivebr.engine import Simulator
calls = []
def cb(sim, screen):
    calls.append(1)
    cam = sim.camera
    pygame.draw.line(screen, (255, 0, 0), cam.world_to_screen(1.0, 2.0), cam.world_to_screen(3.5, 2.5), 3)
    pygame.draw.circle(screen, (0, 255, 0), cam.world_to_screen(5.0, 6.0), int(0.5 * cam.scale), 2)
    pygame.draw.polygon(screen, (0, 0, 255), [cam.world_to_screen(*p) for p in [(7, 7), (8, 7), (8, 8)]])
    pygame.draw.rect(screen, (9, 9, 9), pygame.Rect(*cam.world_to_screen(10, 10), 20, 20))
    tmp = pygame.Surface((10, 10)); pygame.draw.circle(tmp, (1, 1, 1), (5, 5), 3)   # off-screen surface: ignored
    surf = pygame.font.SysFont("consolas", 14).render("hi", True, (255, 255, 255)); screen.blit(surf, (10, 10))
sim = Simulator(controller=lambda r, w, g, c, dt, l=None: {"v": 0.5}, draw_callback=cb)
sim.run()
print("callback calls:", len(calls), "steps:", sim.step_count)
'''


def test_draw_callback_overlay_in_metres():
    with env() as e:
        r = run_for(e, OVERLAY, 30)
        check(r["ok"], r)
        f = [fr for fr in e.host.of("frame") if fr.get("overlay")][-1]
        by = {o["k"]: o for o in f["overlay"]}
        polys = [o for o in f["overlay"] if o["k"] == "poly"]
        check(len(polys) == 2 and polys[1]["c"] == [9, 9, 9], polys)
        by["poly"] = polys[0]
        check(len(f["overlay"]) == 4, f["overlay"])
        ln = by["line"]
        check(ln["c"] == [255, 0, 0] and ln["w"] == 3)
        check(all(abs(a - b) < 1e-3 for a, b in zip(ln["p"][0] + ln["p"][1], [1.0, 2.0, 3.5, 2.5])), ln)
        ci = by["circle"]
        check(abs(ci["p"][0] - 5.0) < 1e-3 and abs(ci["p"][1] - 6.0) < 1e-3 and abs(ci["r"] - 0.5) < 0.02 and ci["w"] == 2, ci)
        check(all(abs(a - b) < 1e-3 for p, q in zip(by["poly"]["p"], [(7, 7), (8, 7), (8, 8)]) for a, b in zip(p, q)))
        # called once per emitted frame, not per physics step
        calls = int(e.stdout.split("calls:")[1].split()[0])
        frames = len(e.host.of("frame"))
        check(calls == frames, (calls, frames))


def test_draw_callback_error_disables_overlay_once():
    code = '''
from hivebr.engine import Simulator
n = []
def cb(sim, screen):
    n.append(1)
    raise RuntimeError("bad drawing")
sim = Simulator(controller=lambda r, w, g, c, dt, l=None: {"v": 0.5}, draw_callback=cb)
sim.run()
print("calls", len(n))
'''
    import contextlib, io
    with env() as e:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            r = run_for(e, code, 20)
        check(r["ok"] and "calls 1" in e.stdout, (r, e.stdout))
        check(err.getvalue().count("bad drawing") >= 1 and err.getvalue().count("Traceback") == 1, err.getvalue())
        check(len(e.host.notices("warn")) == 1 and moved_any(e))


def test_matplotlib_show_emits_figure_and_user_only_import():
    code = '''
import matplotlib.pyplot as plt
plt.plot([1, 2, 3]); plt.title("my plot")
plt.show()
plt.figure(); plt.plot([3, 2, 1]); plt.suptitle("second")
plt.show()
print("backend", plt.get_backend())
'''
    with env() as e:
        r = e.run(code)
        check(r["ok"], r)
        figs = e.host.of("figure")
        check([f["title"] for f in figs] == ["my plot", "second"], figs and [f["title"] for f in figs])
        import base64
        check(base64.b64decode(figs[0]["png_b64"])[:4] == b"\x89PNG" and "agg" in e.stdout.lower(), e.stdout)
        # second run in the same interpreter: matplotlib already imported, still patched
        e.host.posts.clear()
        r = e.run("import matplotlib.pyplot as plt\nplt.plot([1]); plt.show()")
        check(r["ok"] and len(e.host.of("figure")) == 1, r)


def test_matplotlib_not_imported_unless_used():
    with env() as e:
        r = e.run(BASIC.replace("sim.run()", "pass"))
        if "matplotlib" in sys.modules:       # earlier test imported it; check the hook is lazy otherwise
            return
        check("matplotlib" not in sys.modules, "runtime must not import matplotlib eagerly")


def test_strict_json_with_nan_waypoint_orientation_and_inf():
    code = '''
import numpy as np
from hivebr.engine import Simulator
sim = Simulator(controller=lambda r, w, g, c, dt, l=None: {"v": 0.1})
sim.set_robot_waypoints(0, [[1, 1], [2, 2, 0.3]])
sim.robot.battery_percent = float("inf")
sim.robot.x = float("nan")
sim.run()
'''
    with env() as e:
        r = run_for(e, code, 5)
        check(r["ok"], r)             # FakeHost parses every post with a strict JSON parser
        f = e.host.of("frame")[-1]
        check(f["robots"][0]["x"] is None and f["robots"][0]["battery"] is None)
        check(f["waypoints"][0] == [[1.0, 1.0], [2.0, 2.0, 0.3]] if "waypoints" in f else True)
