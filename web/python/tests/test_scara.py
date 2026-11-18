"""SCARA cell: conveyor, colour detection, pick/place, report and template run."""
import csv
import math
import tempfile
from pathlib import Path

from harness import REPO, check, env, run_for

from hivebr_web.scara import BASE_Z, BASKET_Z, BELT_Z, L1, L2, ScaraSimulator

TEMPLATE = REPO / "web" / "templates" / "scara_esteira.py"


def _sim():
    """A stopped simulator: no host loop, deterministic manual steps."""
    sim = ScaraSimulator()
    sim.running = False
    sim.running_simulation = False
    return sim


def _ik(x, y, z):
    """Inverse kinematics used to place the arm exactly on a target."""
    c2 = (x * x + y * y - L1 * L1 - L2 * L2) / (2.0 * L1 * L2)
    q2 = math.acos(max(-1.0, min(1.0, c2)))
    q1 = math.atan2(y, x) - math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    return q1, q2, z - BASE_Z


def test_scara_conveyor_moves_and_detects_colour():
    sim = _sim()
    sim.objects = [{"id": 1, "color": "red", "x": 3.0, "y": 0.0, "z": BELT_Z}]
    sim.conveyor_on(1.0)
    sim._advance(1.0)
    check(sim.objects[0]["x"] < 3.0, "conveyor did not move the part")
    check(sim.colors() == ["red"], "colour detection failed")
    check(sim.next_object()["color"] == "red", "next_object failed")


def test_scara_pick_and_place_uses_matching_basket():
    sim = _sim()
    sim.objects = [{"id": 1, "color": "red", "x": L1 + L2, "y": 0.0, "z": BASE_Z}]
    check(sim.pick(), "pick failed when the tip touches the part")
    check(sim.held is not None and sim.held["color"] == "red", "held part missing")

    basket = sim.basket_for("red")
    sim.arm = dict(zip(("q1", "q2", "d3"), _ik(basket["x"], basket["y"], BASKET_Z)))
    check(sim.can_place(), "can_place failed at the matching basket")
    check(sim.place(), "place failed")
    check(sim.placed == 1, "placed counter not updated")
    check(sim.basket_for("red")["count"] == 1, "basket count not updated")


def test_scara_reports_parts_lost_at_the_belt_start():
    sim = _sim()
    sim.objects = [{"id": 1, "color": "blue", "x": 2.0, "y": 0.0, "z": BELT_Z}]
    sim.conveyor_on(1.0)
    sim._advance(1.0)
    check(sim.rejected == 1, "lost part was not counted")
    check(all(obj["color"] != "blue" for obj in sim.objects), "lost part is still on the belt")


def test_scara_export_writes_a_language_neutral_report():
    sim = _sim()
    sim.placed = 2
    sim.rejected = 1
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "scara_relatorio.csv"
        sim.export(str(path))
        rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    check(rows[0] == ["color", "placed", "lost"], f"unexpected header: {rows[0]}")
    check(["total", "2", "1"] in rows, f"missing totals row: {rows}")


# Reference answers used only by the test: the student fills the same blocks.
_MATRIX_TODO = """    # TODO: monte a matriz com cos/sin de theta e alpha.
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]"""
_MATRIX_OK = """    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return [
        [ct, -st * ca, st * sa, a * ct],
        [st, ct * ca, -ct * sa, a * st],
        [0.0, sa, ca, d],
        [0.0, 0.0, 0.0, 1.0],
    ]"""
_IK_TODO = """    # TODO: lei dos cossenos para q2 e atan2 para q1.
    return 0.0, 0.0, 0.0"""
_IK_OK = """    r2 = x * x + y * y
    c2 = (r2 - L1 * L1 - L2 * L2) / (2.0 * L1 * L2)
    c2 = max(-1.0, min(1.0, c2))
    q2 = math.acos(c2)
    q1 = math.atan2(y, x) - math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    d3 = z - BASE_Z
    return q1, q2, d3"""


def test_scara_template_runs_and_places_parts():
    code = TEMPLATE.read_text(encoding="utf-8")
    check(_MATRIX_TODO in code and _IK_TODO in code, "template TODOs changed; update this test")
    code = code.replace(_MATRIX_TODO, _MATRIX_OK).replace(_IK_TODO, _IK_OK)
    with env() as e:
        result = run_for(e, code, 420)
        check(result["ok"] and result["error"] is None, result)
        check("SCARA OK" in e.stdout, e.stdout[-400:])
        placed = int(e.stdout.rsplit("SCARA OK", 1)[1].split()[0])
        check(placed >= 3, f"the cell placed only {placed} parts")
        check(any(str(f["path"]).endswith("scara_relatorio.csv") for f in result["files"]),
              "scara_relatorio.csv was not written")


# ---------------------------------------------------------- level 5 steps ----
DH_TEMPLATE = REPO / "web" / "templates" / "scara_dh.py"
MATRIZES_TEMPLATE = REPO / "web" / "templates" / "scara_matrizes.py"
URDF_TEMPLATE = REPO / "web" / "templates" / "scara_urdf.py"
URDF_STUDENT = REPO / "web" / "templates" / "scara_cell.urdf"
URDF_REFERENCE = REPO / "web" / "python" / "hivebr_web" / "models" / "scara_cell.urdf"

_DH_TODO = """    # TODO: preencha as tres linhas. Use "q1", "q2" e "d3" para as variaveis
    # de junta e numeros para as dimensoes fixas.
    return [
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
    ]"""
_DH_OK = """    return [
        {"theta": "q1", "d": BASE_Z, "a": 0.0, "alpha": 0.0},
        {"theta": "q2", "d": 0.0, "a": L1, "alpha": 0.0},
        {"theta": 0.0, "d": "d3", "a": L2, "alpha": 0.0},
    ]"""


def test_scara_dh_template_accepts_the_solved_table():
    code = DH_TEMPLATE.read_text(encoding="utf-8")
    check(_DH_TODO in code, "scara_dh TODOs changed; update this test")
    with env() as e:
        result = e.run(code)
        check(result["ok"], result)
        check("DH OK" not in e.stdout, "the placeholder table must not pass")
        result = e.run(code.replace(_DH_TODO, _DH_OK))
        check(result["ok"], result)
        check("DH OK" in e.stdout, e.stdout[-300:])


def test_scara_matrices_template_accepts_the_solved_matrix():
    code = MATRIZES_TEMPLATE.read_text(encoding="utf-8")
    check(_MATRIX_TODO in code, "scara_matrizes TODOs changed; update this test")
    with env() as e:
        result = e.run(code)
        check(result["ok"], result)
        check("MATRIZ OK" not in e.stdout, "the identity matrix must not pass")
        result = e.run(code.replace(_MATRIX_TODO, _MATRIX_OK))
        check(result["ok"], result)
        check("MATRIZ OK" in e.stdout, e.stdout[-300:])


def _write_urdf(e, source):
    folder = e.root / "user_scripts"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "scara_cell.urdf").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def test_scara_urdf_template_checks_the_student_file():
    code = URDF_TEMPLATE.read_text(encoding="utf-8")
    with env() as e:
        _write_urdf(e, URDF_STUDENT)
        result = e.run(code)
        check(result["ok"], result)
        check("URDF OK" not in e.stdout, "the unsolved URDF must not pass")
        _write_urdf(e, URDF_REFERENCE)
        result = e.run(code)
        check(result["ok"], result)
        check("URDF OK" in e.stdout, e.stdout[-300:])
