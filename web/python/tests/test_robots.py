"""Every robot type through the browser simulator: scene, frame extras and log_data."""
import json
import math

from harness import check, env, moved

CMD = {
    "differential": lambda r, w, g, c, dt, l=None: {"v": 0.5, "omega": 0.3},
    "differential_firstorder": lambda r, w, g, c, dt, l=None: {"v": 0.5, "omega": 0.3},
    "boat": lambda r, w, g, c, dt, l=None: {"v": 0.5, "omega": 0.3},
    "holonomic": lambda r, w, g, c, dt, l=None: {"vx": 0.5, "vy": 0.2},
    "hexagonal_holonomic": lambda r, w, g, c, dt, l=None: {"vx": 0.4, "vy": 0.1, "omega": 0.2},
    "ackermann": lambda r, w, g, c, dt, l=None: {"speed": 0.8, "steer": 0.2},
}


def _line_ctrl(robot, world, goal, cfg, dt, lidar=None):
    robot.read_line_sensors(world.line_map)
    return {"v": 0.2, "omega": 2.0 * robot.line_error}


for _t in ("line_follower", "hexagonal_holonomic_line_follower"):
    CMD[_t] = _line_ctrl


def make_track(path, width=2.0, height=1.5, res=0.01):
    from PIL import Image, ImageDraw
    w, h = int(width / res), int(height / res)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    ImageDraw.Draw(img).ellipse([w * 0.15, h * 0.15, w * 0.85, h * 0.85], outline=(0, 0, 0), width=2)
    img.save(path)
    return res


def run_type(e, rtype, steps=40, n_robots=1):
    from hivebr.engine import Simulator, load_config
    cfg = load_config(e.root / "config" / "default.yaml")
    cfg["robot"]["type"] = rtype
    cfg["robot"]["initial_pose"] = [1.0, 2.0, 0.0]
    cfg["waypoints"]["points"] = [[6.0, 4.0]]
    cfg["lidar"]["enabled"] = True
    if "line_follower" in rtype:
        res = make_track(e.root / "config" / "t.png")
        cfg["world"].update(line_map_image=str(e.root / "config" / "t.png"), resolution=res)
        cfg["robot"].update(num_sensors=5, sensor_offset=0.05, line_width=0.02, sensor_aperture=0.004, radius=0.05,
                            length=0.1, width=0.1, max_speed=0.6)
        cfg["robot"]["initial_pose"] = [0.3 + 0.0, 0.75, math.pi / 2]
        cfg["world"]["width"], cfg["world"]["height"] = 2.0, 1.5
    if n_robots > 1:
        cfg["robots"] = [{"id": i, "initial_pose": [1.0 + i, 2.0, 0.0]} for i in range(n_robots)]
    sim = Simulator(config=cfg, controller=CMD[rtype])
    e.host.send(cmd="start")
    e.host.after_frames(steps, cmd="stop")
    sim.run()
    return sim


def test_every_robot_type():
    expect = {
        "differential": ("differential", lambda ex: len(ex["wheel_speeds"]) == 2),
        "differential_firstorder": ("differential_firstorder", lambda ex: "v_ref" in ex),
        "holonomic": ("holonomic", lambda ex: "vx" in ex and "vy" in ex),
        "hexagonal_holonomic": ("hexagonal_holonomic", lambda ex: len(ex["wheel_speeds"]) == 3),
        "ackermann": ("ackermann", lambda ex: "steer" in ex),
        "boat": ("boat", lambda ex: True),
        "line_follower": ("line_follower", lambda ex: len(ex["sensors"]) == 5 and "line_error" in ex),
        "hexagonal_holonomic_line_follower": (
            "hexagonal_holonomic_line_follower", lambda ex: len(ex["sensors"]) == 5 and len(ex["wheel_speeds"]) == 3),
    }
    for rtype, (scene_type, extra_ok) in expect.items():
        with env() as e:
            run_type(e, rtype)
            scene = e.host.of("scene")[-1]
            check(scene["robots"][0]["type"] == scene_type, f"{rtype}: scene type {scene['robots'][0]['type']}")
            frames = e.host.of("frame")
            check(len(frames) >= 40, rtype)
            check(moved(e.host) > 0.05, f"{rtype} did not move")
            r = frames[-1]["robots"][0]
            check(extra_ok(r["extra"]), f"{rtype}: extra {r['extra']}")
            check(r["lidar"] and all(len(p) == 2 for p in r["lidar"]), f"{rtype}: lidar")
            check(r["goal"] == [6.0, 4.0] or "line" in rtype, f"{rtype}: goal {r['goal']}")
            check(r["v"] is not None and r["omega"] is not None, rtype)
            # log_data
            lr = _get_log(e)["robots"][0]
            n = len(lr["t"])
            check(n > 20, f"{rtype}: log length")
            for key in ("x", "y", "theta", "segments"):
                check(len(lr[key]) == n, f"{rtype}: {key} length")
            check(len(lr["v"]) == n and len(lr["omega"]) == n, f"{rtype}: v/omega missing")
            if rtype != "holonomic" and "hexagonal" not in rtype and "line" not in rtype:
                check(len(lr["v_cmd"]) == n, f"{rtype}: v_cmd")
            check(lr["type"] == scene_type, rtype)


def _get_log(e):
    from hivebr_web import commands, simulator
    sim = simulator._current
    commands.dispatch(sim, json.dumps({"cmd": "get_log", "open": True}))
    data = e.host.of("log_data")[-1]
    check(data["open"] is True)
    return data


def test_ackermann_log_has_steer_and_yaw_rate():
    with env() as e:
        run_type(e, "ackermann")
        data = _get_log(e)["robots"][0]
        check(len(data["steer"]) == len(data["t"]) and abs(data["steer_cmd"][-1] - 0.2) < 1e-6)
        wb = 0.285
        check(abs(data["omega_cmd"][-1] - 0.8 / wb * math.tan(0.2)) < 1e-3, data["omega_cmd"][-1])


def test_holonomic_log_speed_is_norm():
    with env() as e:
        run_type(e, "holonomic")
        data = _get_log(e)["robots"][0]
        check(abs(data["v"][-1] - math.hypot(0.5, 0.2)) < 1e-3 and len(data["omega"]) == len(data["t"]), data["v"][-3:])


def test_multi_robot_frame_and_collisions_total():
    with env() as e:
        sim = run_type(e, "differential", n_robots=3)
        f = e.host.of("frame")[-1]
        check([r["id"] for r in f["robots"]] == [0, 1, 2])
        check(f["collisions_total"] == len(sim.collision_events))
        check(len(e.host.of("scene")[-1]["robots"]) == 3)
