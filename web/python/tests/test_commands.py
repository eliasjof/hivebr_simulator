"""Every host command: dispatches without raising and has the desktop-equivalent effect."""
import base64
import io
import json

import yaml

from harness import check, env


def make_sim(e, robots=2):
    from hivebr.engine import Simulator, load_config
    cfg = load_config(e.root / "config" / "default.yaml")
    cfg["robots"] = [{"id": i, "initial_pose": [1.0 + i, 2.0, 0.0]} for i in range(robots)]
    cfg["lidar"]["enabled"] = False
    return Simulator(config=cfg, controller=lambda r, w, g, c, dt, l=None: {"v": 0.5, "omega": 0.2})


def cmd(sim, **msg):
    from hivebr_web import commands
    commands.dispatch(sim, json.dumps(msg))


def frame(e, sim):
    sim._dirty = True
    sim._emit()
    return e.host.of("frame")[-1]


def png_b64(img):
    buf = io.BytesIO(); img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_run_state_commands():
    with env() as e:
        sim = make_sim(e)
        cmd(sim, cmd="start"); check(sim.running_simulation)
        cmd(sim, cmd="pause"); check(not sim.running_simulation)
        cmd(sim, cmd="toggle"); check(sim.running_simulation)
        cmd(sim, cmd="toggle"); check(not sim.running_simulation)
        t0 = sim.sim_time
        cmd(sim, cmd="step_once")
        check(abs(sim.sim_time - t0 - sim.dt) < 1e-9 and not sim.running_simulation, "step_once")
        check(sim.robots[0].x > 1.0, "robot should move on step_once")
        cmd(sim, cmd="start"); cmd(sim, cmd="reset")
        check(not sim.running_simulation and sim.sim_time == 0.0 and sim.robots[0].x == 1.0, "reset")
        cmd(sim, cmd="set_speed", factor=2.5); check(sim.speed == 2.5)
        cmd(sim, cmd="set_speed", factor=0); check(sim.speed == 0)
        cmd(sim, cmd="select_robot", index=1); check(sim.selected_robot_index == 1 and sim.robot is sim.robots[1])
        check(frame(e, sim)["selected"] == 1)
        cmd(sim, cmd="stop"); check(sim.running is False)
        check(not e.host.notices(), e.host.notices())


def test_waypoint_commands():
    with env() as e:
        sim = make_sim(e)
        cmd(sim, cmd="add_waypoint", robot=1, x=3, y=4, theta=1.5)
        cmd(sim, cmd="add_waypoint", robot=1, x=5, y=6)             # define_orientation=true in default.yaml
        check([list(w) for w in sim.waypoint_managers[1].waypoints] == [[3, 4, 1.5], [5, 6, 0.0]])
        cmd(sim, cmd="add_waypoint", x=1, y=1)                       # selected robot (0)
        check(len(sim.waypoint_managers[0].waypoints) == 1)
        f = frame(e, sim)
        check(f["waypoints"][1] == [[3.0, 4.0, 1.5], [5.0, 6.0, 0.0]] and f["wp_version"] > 0)
        sim.waypoint_managers[1].current_index = 1
        cmd(sim, cmd="remove_waypoint", robot=1, index=0)
        check(len(sim.waypoint_managers[1].waypoints) == 1 and sim.waypoint_managers[1].current_index == 0)
        cmd(sim, cmd="clear_waypoints", robot=1)
        check(not sim.waypoint_managers[1].waypoints and len(sim.waypoint_managers[0].waypoints) == 1)
        cmd(sim, cmd="add_waypoint", robot=1, x=2, y=2)
        cmd(sim, cmd="clear_waypoints")
        check(all(not m.waypoints for m in sim.waypoint_managers))
        v = frame(e, sim)["wp_version"]
        check(v == frame(e, sim)["wp_version"] and "waypoints" not in frame(e, sim), "waypoints resent without change")
        check(not e.host.notices(), e.host.notices())


def test_obstacle_and_recharge_commands():
    with env() as e:
        sim = make_sim(e)
        n0 = len(sim.world.obstacles)
        cmd(sim, cmd="add_obstacle", x=4, y=5, r=0.7)
        check(list(sim.world.obstacles[-1]) == [4, 5, 0.7] and len(sim.config["world"]["obstacles"]) == n0 + 1)
        f = frame(e, sim)
        check([4.0, 5.0, 0.7] in f["obstacles"] and f["obstacles_version"] > 0)
        cmd(sim, cmd="remove_obstacle", index=n0)
        check(len(sim.world.obstacles) == n0)
        cmd(sim, cmd="add_recharge", x=7, y=8)
        check(frame(e, sim)["recharge"] == [[7.0, 8.0]])
        cmd(sim, cmd="add_recharge", x=1, y=2)
        cmd(sim, cmd="remove_recharge", index=0)
        check(frame(e, sim)["recharge"] == [[1.0, 2.0]], "remove_recharge")
        cmd(sim, cmd="remove_recharge", index=0)
        check(frame(e, sim)["recharge"] == [])
        cmd(sim, cmd="add_recharge", x=7, y=8)
        cmd(sim, cmd="add_obstacle", x=1, y=1, r=0.2); frame(e, sim)
        cmd(sim, cmd="clear_obstacles"); check(len(sim.world.obstacles) == 0)
        check(frame(e, sim)["obstacles"] == [])
        check(not e.host.notices(), e.host.notices())


def test_path_and_pose_commands():
    with env() as e:
        sim = make_sim(e)
        cmd(sim, cmd="start")
        for _ in range(20):
            sim.step()
        check(len(sim.robots[0].path) > 0)
        ep = frame(e, sim)["robots"][0]["path_epoch"]
        cmd(sim, cmd="clear_path", robot=0)
        check(not sim.robots[0].path and sim.robots[1].path)
        check(frame(e, sim)["robots"][0]["path_epoch"] > ep, "path_epoch not bumped")
        cmd(sim, cmd="clear_path")
        check(not sim.robots[1].path)
        sim.reset(); sim.running_simulation = False
        cmd(sim, cmd="set_pose", robot=1, x=9, y=8, theta=0.5)
        r = sim.robots[1]
        check((r.x, r.y, r.theta) == (9, 8, 0.5) and list(r.initial_pose) == [9, 8, 0.5])
        # after the run started, set_pose keeps the initial pose (reset still goes back)
        cmd(sim, cmd="start"); [sim.step() for _ in range(3)]
        cmd(sim, cmd="set_pose", robot=1, x=2, y=2, theta=0)
        check(list(r.initial_pose) == [9, 8, 0.5] and r.x == 2)


def test_set_param_matches_sliders():
    with env() as e:
        sim = make_sim(e)
        cmd(sim, cmd="set_param", name="max_speed", value=1.25)
        check(all(r.max_speed == 1.25 for r in sim.robots) and sim.config["robot"]["max_speed"] == 1.25)
        cmd(sim, cmd="set_param", name="max_omega", value=2.0)
        check(all(r.max_omega == 2.0 for r in sim.robots))
        cmd(sim, cmd="set_param", name="max_steer", value=0.3)       # no attribute on differential: untouched
        check(sim.config["robot"]["max_steer"] == 0.3 and not hasattr(sim.robots[0], "max_steer"))
        cmd(sim, cmd="set_param", name="grid_size", value=2.0)
        check(sim.world.grid_size == 2.0 and sim.config["world"]["grid_size"] == 2.0)
        cmd(sim, cmd="set_param", name="noise_sigma", value=0.2)
        n = sim.config["noise"]
        check(n["enabled"] and n["sigma_v"] == 0.2 and n["sigma_omega"] == 0.2)
        cmd(sim, cmd="set_param", name="noise_sigma", value=0)
        check(not sim.config["noise"]["enabled"])
        cmd(sim, cmd="set_param", name="servo_max_speed", value=10)
        check(sim.config["robot"]["servo_max_speed"] == 10)
        cmd(sim, cmd="set_param", name="goal_tolerance", value=0.6)
        check(all(m.goal_tolerance == 0.6 for m in sim.waypoint_managers) and sim.config["waypoints"]["goal_tolerance"] == 0.6)
        cmd(sim, cmd="set_param", name="max_speed", value=99)         # clamped to the slider range
        check(sim.robots[0].max_speed == 8.0)
        f = frame(e, sim)
        sc = e.host.of("scene")[-1]
        check(sc["params"]["grid_size"] == 2.0 and sc["waypoints_cfg"]["goal_tolerance"] == 0.6, "scene not refreshed")
        check(not e.host.notices(), e.host.notices())
        cmd(sim, cmd="set_param", name="bogus", value=1)
        check(e.host.notices("warn"))


def test_toggles():
    with env() as e:
        sim = make_sim(e)
        cmd(sim, cmd="toggle_lidar"); check(sim.lidar.enabled)
        cmd(sim, cmd="start"); sim.step()
        f = frame(e, sim)
        check(f["robots"][0]["lidar"] and e.host.of("scene")[-1]["lidar"]["enabled"])
        cmd(sim, cmd="toggle_lidar"); check(not sim.lidar.enabled and frame(e, sim)["robots"][0]["lidar"] is None)
        cmd(sim, cmd="toggle_noise"); check(sim.config["noise"]["enabled"])
        frame(e, sim); check(e.host.of("scene")[-1]["noise"]["enabled"])
        cmd(sim, cmd="toggle_noise"); check(not sim.config["noise"]["enabled"])
        sim.apply_theme("dark")
        cmd(sim, cmd="toggle_theme"); check(sim.config["theme"] == "light")
        frame(e, sim); check(e.host.of("scene")[-1]["theme"] == "light")
        cmd(sim, cmd="toggle_times"); check(sim.config["show_times"] is False)


def test_map_commands():
    from PIL import Image
    with env() as e:
        sim = make_sim(e)
        img = Image.new("L", (50, 30), 255)
        img.putpixel((0, 0), 0)                       # top-left pixel = (x=0, y=max)
        for x in range(10, 20):
            img.putpixel((x, 29), 0)                  # bottom row = y near 0
        cmd(sim, cmd="load_map", name="m.png", b64=png_b64(img), resolution=0.2)
        gm = sim.world.grid_map
        check(gm is not None and sim.grid_map is gm and abs(sim.world.width - 10.0) < 1e-9 and abs(sim.world.height - 6.0) < 1e-9, (gm, sim.world.width, sim.world.height, e.host.notices()))
        check(gm.is_occupied(0.1, 5.9) and gm.is_occupied(2.5, 0.1) and not gm.is_occupied(5, 3), "map orientation")
        f = frame(e, sim)
        m = e.host.of("scene")[-1]["map"]
        png = Image.open(io.BytesIO(base64.b64decode(m["png_b64"])))
        check(png.size == (50, 30) and png.getpixel((0, 0)) == 0 and png.getpixel((12, 29)) == 0 and png.getpixel((30, 15)) == 255)
        check(m["width_m"] == 10.0 and m["resolution"] == 0.2 and m["kind"] == "occupancy")
        check(m["inflated_png_b64"], "inflated map expected")
        cmd(sim, cmd="load_map", name="x.png", b64="@@@", resolution=0.2)
        check(e.host.notices())
        cmd(sim, cmd="clear_map")
        check(sim.world.grid_map is None and sim.grid_map is None)
        frame(e, sim); check(e.host.of("scene")[-1]["map"] is None)


def test_notices_carry_code_and_params():
    with env() as e:
        sim = make_sim(e, robots=1)
        cmd(sim, cmd="no_such_command")
        cmd(sim, cmd="export_log", format="csv")        # nothing logged yet
        cmd(sim, cmd="load_map", name="x.png", b64="@@@", resolution=0.2)
        ns = e.host.notices()
        codes = [n.get("code") for n in ns]
        check("unknown_command" in codes and "no_log_data" in codes and "map_load_failed" in codes, ns)
        u = [n for n in ns if n.get("code") == "unknown_command"][0]
        check(u["params"] == {"name": "no_such_command"} and "Unknown command" in u["text"], u)
        check(all(isinstance(n["text"], str) and n["text"] for n in ns), "text fallback must stay")


def test_load_line_map_kind():
    from PIL import Image
    with env() as e:
        sim = make_sim(e, robots=1)
        img = Image.new("L", (60, 40), 255)
        for x in range(0, 60):
            for y in range(18, 22):
                img.putpixel((x, y), 0)               # horizontal black band at mid height
        cmd(sim, cmd="load_map", name="pista.png", b64=png_b64(img), resolution=0.1, kind="line")
        lm = sim.world.line_map
        check(lm is not None and sim.world.grid_map is None, (lm, e.host.notices()))
        check(abs(sim.world.width - 6.0) < 1e-9 and abs(sim.world.height - 4.0) < 1e-9, "world resized to the track")
        check(lm.sample(3.0, 2.0) > 0.5 and lm.sample(3.0, 0.3) < 0.1, "band sampled where drawn")
        frame(e, sim)
        sc = e.host.of("scene")[-1]
        check(sc["lineMap"] is not None and sc["map"] is None and sc["lineMap"]["png_b64"], "scene re-posted with lineMap")
        # sensors of a line follower read the new track
        robot = sim.robots[0]
        if hasattr(robot, "read_line_sensors"):
            robot.x, robot.y, robot.theta = 3.0, 2.0, 0.0
            vals = robot.read_line_sensors(sim.world.line_map)
            check(float(max(vals)) > 0.5, "line-follower sensors should see the track")
        cmd(sim, cmd="load_map", name="m.png", b64=png_b64(img), resolution=0.1, kind="bogus")
        cmd(sim, cmd="clear_map")
        check(sim.world.line_map is None)
        frame(e, sim); check(e.host.of("scene")[-1]["lineMap"] is None)


def test_track_commands():
    from PIL import Image
    with env() as e:
        sim = make_sim(e, robots=1)
        strokes = [[[2.0, 3.0], [4.0, 3.0], [6.0, 3.5], [8.0, 3.5]]]
        cmd(sim, cmd="track_apply", strokes=strokes)
        lm = sim.world.line_map
        check(lm is not None and sim.config["world"]["line_map_image"], "no line map applied")
        check(lm.sample(3.0, 3.0) > 0.5 and lm.sample(3.0, 8.0) < 0.1, "stroke not rasterized in the right place")
        r = sim.robots[0]
        check(abs(r.x - 2.0) < 1e-6 and abs(r.y - 3.0) < 1e-6, "robot not placed on track start")
        check((e.root / "config" / "line_drawn.png").exists())
        f = frame(e, sim)
        lmi = e.host.of("scene")[-1]["lineMap"]
        png = Image.open(io.BytesIO(base64.b64decode(lmi["png_b64"])))
        check(png.size == (200, 120) and png.getpixel((30, 120 - 1 - 30)) == 0, "line map png orientation")
        cmd(sim, cmd="track_export")
        fm = e.host.of("file")[-1]
        check(fm["name"] == "track.png" and fm["mime"] == "image/png" and base64.b64decode(fm["b64"])[:4] == b"\x89PNG")
        cmd(sim, cmd="track_clear")
        check(sim._track_gray is None and not sim.track_editor.has_content)
        check(not e.host.notices("warn"), e.host.notices())


def test_files_and_log_commands():
    with env() as e:
        sim = make_sim(e)
        cmd(sim, cmd="export_log", format="csv")
        check(e.host.notices("warn"), "export without data should warn")
        cmd(sim, cmd="start")
        for _ in range(30):
            sim.step()
        cmd(sim, cmd="save_config")
        cfg = e.host.of("file")[-1]
        check(cfg["name"] == "config.yaml" and "robots" in yaml.safe_load(base64.b64decode(cfg["b64"])))
        cmd(sim, cmd="export_log", format="csv")
        csv = [f for f in e.host.of("file") if f["name"] == "hivebr_log.csv"][-1]
        text = base64.b64decode(csv["b64"]).decode()
        check(text.startswith("robot,robot_type,segment,t,x,y,theta") and len(text.splitlines()) > 30)
        cmd(sim, cmd="export_log", format="pkl")
        pkl = [f for f in e.host.of("file") if f["name"] == "hivebr_log.pkl"][-1]
        check(len(base64.b64decode(pkl["b64"])) > 100)
        cmd(sim, cmd="get_log", open=False)
        log = e.host.of("log_data")[-1]
        check(log["open"] is False and len(log["robots"]) == 2 and len(log["robots"][0]["t"]) >= 29, log["robots"][0].keys())
        check(set(log["robots"][0]) >= {"id", "type", "color", "t", "x", "y", "theta", "v", "omega", "v_cmd",
                                        "omega_cmd", "err_pos", "err_theta", "segments"})
        cmd(sim, cmd="reset_logger")
        cmd(sim, cmd="get_log", open=True)
        check(e.host.of("log_data")[-1]["robots"] == [] and e.host.of("log_data")[-1]["open"] is True)


def test_log_plot_hook_opens_window():
    with env() as e:
        sim = make_sim(e)
        cmd(sim, cmd="start")
        for _ in range(10):
            sim.step()
        sim.logger.plot()
        check(e.host.of("log_data")[-1]["open"] is True and e.host.of("log_data")[-1]["robots"])


def test_refresh_and_bad_commands_never_raise():
    with env() as e:
        sim = make_sim(e)
        n_scene, n_frame = len(e.host.of("scene")), len(e.host.of("frame"))
        cmd(sim, cmd="refresh")
        sim._emit()
        check(len(e.host.of("scene")) == n_scene + 1 and len(e.host.of("frame")) == n_frame + 1)
        check("waypoints" in e.host.of("frame")[-1] and "obstacles" in e.host.of("frame")[-1], "refresh must resend statics")
        from hivebr_web import commands
        bad = ['{"cmd": "nope"}', "not json", "{}", '{"cmd": "add_waypoint", "x": "abc", "y": 1}',
               '{"cmd": "select_robot"}', '{"cmd": "set_param", "name": "max_speed", "value": NaN}',
               '{"cmd": "remove_obstacle", "index": 99}', '{"cmd": "add_waypoint", "robot": 9, "x": 1, "y": 1}',
               '{"cmd": "set_speed", "factor": "fast"}', '{"cmd": "load_map"}', "[]", "null", "42"]
        for raw in bad:
            before = len(e.host.notices("warn"))
            commands.dispatch(sim, raw)
            check(len(e.host.notices("warn")) == before + 1, f"no warn for {raw}")
        sim._emit()
        check(sim.speed == 1.0 and sim.running)
