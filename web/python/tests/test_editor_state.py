"""Idle editor: edits made without a run are merged into later simulators."""
import base64
import io
import json

from harness import check, env


def make_sim(e, robots=2):
    from hivebr.engine import Simulator, load_config
    cfg = load_config(e.root / "config" / "default.yaml")
    cfg["robots"] = [{"id": i, "initial_pose": [1.0 + i, 2.0, 0.0]} for i in range(robots)]
    cfg["lidar"]["enabled"] = False
    return Simulator(config=cfg, controller=lambda *a, **k: {"v": 0.0, "omega": 0.0})


def edit(e, **cmd):
    """UI command while idle (same entry point as the worker `edit` message)."""
    e.runner.dispatch_edit(json.dumps(cmd))


def editor(e):
    return e.runner.ensure_editor()


def png_b64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_idle_editor_exists_and_ignores_run_controls():
    with env() as e:
        sim = editor(e)
        check(sim is editor(e), "the editor must be a singleton")
        check(e.host.of("scene") and e.host.of("frame"), "the editor must post its scene")
        check(not sim.running_simulation and not sim.running)
        edit(e, cmd="start")
        edit(e, cmd="pause")
        edit(e, cmd="stop")
        edit(e, cmd="step_once")
        check(not sim.running_simulation and not sim.running, "run controls must be ignored while editing")
        edit(e, cmd="add_obstacle", x=4, y=5, r=0.7)
        edit(e, cmd="add_recharge", x=7, y=8)
        edit(e, cmd="add_waypoint", robot=0, x=3, y=4, theta=1.5)
        edit(e, cmd="set_pose", robot=0, x=9, y=8, theta=0.5)
        edit(e, cmd="set_param", name="max_speed", value=1.25)
        check([4.0, 5.0, 0.7] in [list(o) for o in sim.world.obstacles])
        check([3.0, 4.0, 1.5] in [list(w) for w in sim.waypoint_managers[0].waypoints])
        check((sim.robots[0].x, sim.robots[0].y, sim.robots[0].theta) == (9.0, 8.0, 0.5))
        check(sim.robots[0].max_speed == 1.25)
        f = e.host.of("frame")[-1]
        check([4.0, 5.0, 0.7] in f["obstacles"] and [7.0, 8.0] in f["recharge"])
        check(not e.host.notices("warn"), e.host.notices())


def test_collection_and_single_edits_are_applied_to_new_simulators():
    with env() as e:
        edit(e, cmd="add_obstacle", x=4, y=5, r=0.7)
        edit(e, cmd="add_recharge", x=7, y=8)
        edit(e, cmd="add_waypoint", robot=0, x=3, y=4, theta=1.5)
        edit(e, cmd="set_pose", robot=0, x=9, y=8, theta=0.5)
        edit(e, cmd="set_param", name="max_speed", value=1.25)
        sim = make_sim(e)
        check([4.0, 5.0, 0.7] in [list(o) for o in sim.world.obstacles])
        check([3.0, 4.0, 1.5] in [list(w) for w in sim.waypoint_managers[0].waypoints])
        check([7.0, 8.0] in [list(p)[:2] for p in sim.world.recharge_places])
        check(sim.robots[0].max_speed == 1.25)
        check((sim.robots[0].x, sim.robots[0].y, sim.robots[0].theta) == (9.0, 8.0, 0.5))
        check(list(sim.robots[0].initial_pose) == [9.0, 8.0, 0.5], "reset must keep the edited pose")


def test_commands_during_a_run_are_remembered():
    code = '''
from hivebr.engine import Simulator, load_config
cfg = load_config("config/default.yaml")
cfg["lidar"]["enabled"] = False
sim = Simulator(config=cfg, controller=lambda r, w, g, c, dt, l=None: {"v": 0.2, "omega": 0.0})
sim.run()
'''
    with env() as e:
        e.host.send(cmd="start")
        e.host.after_frames(10, cmd="add_obstacle", x=4, y=5, r=0.7)
        e.host.after_frames(20, cmd="stop")
        r = e.run(code)
        check(r["ok"], r)
        sim = make_sim(e)
        check([4.0, 5.0, 0.7] in [list(o) for o in sim.world.obstacles])


def test_post_run_editor_adopts_scene_and_removals():
    code = '''
from hivebr.engine import Simulator, load_config
cfg = load_config("config/default.yaml")
cfg["lidar"]["enabled"] = False
cfg["robots"] = [{"id": 0, "initial_pose": [1.0, 2.0, 0.0],
                  "waypoints": [[3.0, 4.0, 0.0], [5.0, 6.0, 0.0]]}]
cfg["world"]["obstacles"] = [[6.0, 5.0, 0.4]]
sim = Simulator(config=cfg)
'''
    with env() as e:
        r = e.run(code)
        check(r["ok"], r)
        from hivebr_web import simulator
        sim = simulator.editor()
        check(sim is not None and not sim.running and not sim.running_simulation)
        check(len(sim.waypoint_managers[0].waypoints) == 2)
        edit(e, cmd="remove_waypoint", robot=0, index=0)
        edit(e, cmd="remove_obstacle", index=0)
        r = e.run(code)
        check(r["ok"], r)
        sim = simulator.editor()
        check([list(w) for w in sim.waypoint_managers[0].waypoints] == [[5.0, 6.0, 0.0]])
        check(not sim.world.obstacles, "removed obstacle came back")


def test_map_and_track_edits_persist():
    from PIL import Image
    with env() as e:
        img = Image.new("L", (50, 30), 255)
        edit(e, cmd="load_map", name="m.png", b64=png_b64(img), resolution=0.2)
        sim = make_sim(e)
        check(sim.world.grid_map is not None and abs(sim.world.width - 10.0) < 1e-9)

        edit(e, cmd="clear_map")
        sim = make_sim(e)
        check(sim.world.grid_map is None and sim.world.line_map is None)

        edit(e, cmd="track_apply", strokes=[[[2.0, 3.0], [6.0, 3.0]]], line_width=0.1)
        sim = make_sim(e)
        check(sim.world.line_map is not None)
        check(sim.world.line_map.sample(4.0, 3.0) > 0.5, "track stroke missing")
        check(abs(sim.robots[0].x - 2.0) < 1e-6 and abs(sim.robots[0].y - 3.0) < 1e-6)

        edit(e, cmd="track_clear")
        sim = make_sim(e)
        check(sim.world.line_map is None)
        check(not e.host.notices("warn"), e.host.notices())


def test_reset_config_forgets_recorded_parameters():
    import shutil
    with env() as e:
        target = e.root / "config" / "default.yaml"
        shutil.copyfile(target, e.root / "config" / ".default.orig.yaml")
        edit(e, cmd="set_param", name="max_speed", value=1.25)
        check(make_sim(e).robots[0].max_speed == 1.25)
        edit(e, cmd="reset_config")
        check(make_sim(e).robots[0].max_speed != 1.25)
