"""README quick start, controllers and the runnable examples, run verbatim."""
from harness import REPO, check, env, moved, run_for

QUICKSTART = '''
from hivebr import HiveBrAgent, SwarmExperiment

class Patrol(HiveBrAgent):
    def loop(self, state, neighbors):
        # state.goal holds the current waypoint (x, y, theta)
        return 0.5, 0.0

exp = SwarmExperiment(robots=3, backend="navsim2d")
exp.assign_agent(robot_ids=[0, 1, 2], agent_class=Patrol)
exp.assign_route(0, [[5, 2, 0.0], [5, 6, 0.0]])
exp.run()
print("after run")
'''

CENTRALIZED = '''
from hivebr import SwarmController, SwarmExperiment

class Cmd(SwarmController):
    def loop(self, states):
        return {rid: (0.4, 0.2) for rid in states}

exp = SwarmExperiment(robots=2)
exp.set_controller(Cmd())
exp.run()
print("log frames:", sum(len(l.frames) for l in exp.simulator.logger.result().logs.values()))
'''


def test_quickstart_readme():
    with env() as e:
        r = run_for(e, QUICKSTART, 50)
        check(r["ok"] and r["error"] is None, r)
        check("after run" in e.stdout, "code after exp.run() did not execute")
        check(len(e.host.of("frame")[0]["robots"]) == 3)
        check(moved(e.host) > 0.3, "robots did not move")
        check(e.host.of("frame")[-1]["running"] is False, "final frame should be stopped")


def test_swarm_controller_centralized():
    with env() as e:
        r = run_for(e, CENTRALIZED, 40)
        check(r["ok"], r)
        check("log frames:" in e.stdout and "log frames: 0" not in e.stdout, e.stdout)
        check(moved(e.host) > 0.2)


def test_swarm_decentralized_agent_config():
    code = '''
from hivebr import HiveBrAgent, SwarmExperiment
seen = {}
class A(HiveBrAgent):
    def setup(self): seen["tol"] = self.cfg["waypoints"]["goal_tolerance"]
    def loop(self, state, neighbors):
        seen["n"] = len(neighbors); return (0.3, 0.1)
exp = SwarmExperiment(robots=2, goal_tolerance=0.25)
exp.assign_agent(robot_ids=[0, 1], agent_class=A)
exp.run()
print("seen", seen)
'''
    with env() as e:
        r = run_for(e, code, 20)
        check(r["ok"], r)
        check("'tol': 0.25" in e.stdout and "'n': 1" in e.stdout, e.stdout)


def test_example_controle_robodiferencial():
    with env() as e:
        r = run_for(e, (REPO / "examples/controle_robodiferencial.py").read_text(), 120)
        check(r["ok"], r)
        check(moved(e.host) > 1.0, "robot did not move")
        check(e.host.of("frame")[-1]["robots"][0]["battery_enabled"], "battery model not reported")
        check(len(e.host.of("frame")[-1]["robots"]) == 1)
        sent = [f["recharge"] for f in e.host.of("frame") if "recharge" in f]
        check(sent and len(sent[-1]) == 3, "recharge places missing")


def test_example_decentralized_swarm():
    with env() as e:
        r = run_for(e, (REPO / "examples/decentralized_swarm.py").read_text(), 100)
        check(r["ok"], r)
        check(moved(e.host) > 0.5)
        check("[DataLogger]" in e.stdout, "code after exp.run() (save_log) did not execute")
        check(any(f["path"].endswith("decentralized_swarm_log.pkl") for f in r["files"]), r["files"])
        last = e.host.of("frame")[-1]
        check(last["links"] is not None and len(last["robots"]) == 4)
        check(last["robots"][0]["lidar"], "lidar hits missing")


def test_example_line_follower():
    with env() as e:
        r = run_for(e, (REPO / "examples/line_follower.py").read_text(), 150)
        check(r["ok"], r)
        check(moved(e.host) > 0.2)
        check("Simulação encerrada" in e.stdout or "volta" in e.stdout or "Percurso" in e.stdout, e.stdout[-200:])
        sc = e.host.of("scene")[-1]
        check(sc["lineMap"] and sc["lineMap"]["png_b64"], "line map not in scene")
        ex = e.host.of("frame")[-1]["robots"][0]["extra"]
        check(len(ex["sensors"]) == 5 and "line_error" in ex and "lap_times" in ex, ex.keys())
        check(any(f["path"].endswith("line_track.png") for f in r["files"]))


def test_example_multi_line_follower():
    with env() as e:
        r = run_for(e, (REPO / "examples/multi_line_follower.py").read_text(), 100)
        check(r["ok"], r)
        check("Resultado por robô" in e.stdout and e.stdout.count("B-Bot") >= 8, e.stdout[-300:])
        check(moved(e.host) > 0.2)


def test_example_multi_robot_differential():
    with env() as e:
        r = run_for(e, (REPO / "examples/multi_robot_differential.py").read_text(), 100)
        check(r["ok"], r)
        check(len(e.host.of("frame")[-1]["robots"]) == 4 and moved(e.host) > 0.5)
        check(e.host.of("frame")[-1]["robots"][0]["lidar"] is not None)


def test_example_hexagonal_holonomic():
    with env() as e:
        r = run_for(e, (REPO / "examples/run_hexagonal_holonomic.py").read_text(), 80)
        check(r["ok"], r)
        check(moved(e.host) > 0.1)
        rob = e.host.of("frame")[-1]["robots"][0]
        check(len(rob["extra"]["wheel_speeds"]) == 3, rob["extra"])
        check(e.host.of("scene")[-1]["robots"][0]["type"] == "hexagonal_holonomic")


def test_example_hexagonal_holonomic_line_follower():
    with env() as e:
        r = run_for(e, (REPO / "examples/run_hexagonal_holonomic_line_follower.py").read_text(), 120)
        check(r["ok"], r)
        check(moved(e.host) > 0.1)
        check("Lap" in e.stdout or "Track" in e.stdout or "ended" in e.stdout or "summary" in e.stdout, e.stdout[-300:])
        ex = e.host.of("frame")[-1]["robots"][0]["extra"]
        check(ex["sensors"] and len(ex["wheel_speeds"]) == 3)
        check(e.host.of("scene")[-1]["robots"][0]["type"] == "hexagonal_holonomic_line_follower")


def test_examples_rerun_is_fresh():
    """Second run of the same example imports it again (modules purged)."""
    with env() as e:
        run_for(e, (REPO / "examples/line_follower.py").read_text(), 20)
        check(not any(m == "line_follower" for m in __import__("sys").modules))
        e.host.posts.clear(); e.host.frames = 0
        r = run_for(e, (REPO / "examples/multi_line_follower.py").read_text(), 20)
        check(r["ok"], r)


def test_decentralized_multiprocess_and_broken_examples():
    """Documents the examples that cannot run (informational, asserts the failure mode)."""
    with env() as e:
        r = e.run((REPO / "examples/run_holonomic.py").read_text())
        check(not r["ok"] and r["error"]["type"] == "ModuleNotFoundError"
              and "vortex_apf" in r["error"]["message"], r)
    with env() as e:
        src = (REPO / "examples/decentralized_multiprocess.py").read_text()
        check("ProcessPoolExecutor" in src)
    with env() as e:
        r = e.run("import examples.controllers.potential_field as pf; print('pf ok')")
        check(r["ok"] and "pf ok" in e.stdout, r)
        r = e.run("import examples.controllers.planner_controller")
        check(not r["ok"] and "base_planner" in r["error"]["message"], r)
