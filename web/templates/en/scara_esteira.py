"""Activity: SCARA cell with conveyor, colour detection and baskets.

The conveyor brings red, green and blue parts. The 3-joint SCARA arm
(q1, q2 and the prismatic d3) must pick each part and place it in the basket
of the same colour. The simulator provides the part positions; the kinematics
is yours.

Complete, in this order:
  1. tabela_dh(): the Denavit-Hartenberg table of the SCARA.
  2. matriz_transformacao(): the 4x4 homogeneous matrix of one DH row.
  3. cinematica_direta(): multiply the matrices and return (x, y, z).
  4. cinematica_inversa(): law of cosines to find (q1, q2, d3).

The scara_cell.urdf file is also part of the activity: it defines the shoulder
height and both arm lengths. If the URDF is wrong, the robot cannot reach the
conveyor. Fill the URDF TODOs before running.

Hints:
  - The reach is L1 + L2 = 3.0 m; the base sits at BASE_Z.
  - Use math.atan2(y, x) and math.acos() with the argument clamped to [-1, 1].
  - The gripper only picks when the tip is within 30 cm of the part.

The script prints SCARA OK at the end and writes scara_relatorio.csv.
"""

import math

from hivebr_web.scara import BASE_Z, L1, L2, ScaraSimulator


def tabela_dh():
    """SCARA DH table: one row per joint.

    Each row has theta, d, a and alpha. Replace the placeholders with the
    numeric values or the joint variables.
    """
    # TODO: fill in the SCARA DH table.
    return [
        {"theta": "q1", "d": "d1", "a": "a1", "alpha": "alpha1"},
        {"theta": "q2", "d": "d2", "a": "a2", "alpha": "alpha2"},
        {"theta": "0", "d": "d3", "a": "a3", "alpha": "alpha3"},
    ]


def multiplicar(a, b):
    """Multiplies two 4x4 matrices."""
    return [
        [sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]


def matriz_transformacao(theta, d, a, alpha):
    """4x4 homogeneous matrix of one DH row (classic convention)."""
    # TODO: build the matrix with cos/sin of theta and alpha.
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def cinematica_direta(q1, q2, d3):
    """Returns the tip (x, y, z) for the joints (q1, q2, d3)."""
    # TODO: use tabela_dh() and matriz_transformacao().
    t1 = matriz_transformacao(q1, BASE_Z, 0.0, 0.0)
    t2 = matriz_transformacao(q2, 0.0, L1, 0.0)
    t3 = matriz_transformacao(0.0, d3, L2, 0.0)
    t = multiplicar(multiplicar(t1, t2), t3)
    return t[0][3], t[1][3], t[2][3]


def cinematica_inversa(x, y, z):
    """Returns (q1, q2, d3) for the tip at (x, y, z)."""
    # TODO: law of cosines for q2 and atan2 for q1.
    return 0.0, 0.0, 0.0


def controlar(sim):
    """Main loop: conveyor, colour detection, pick and place."""
    print("DH", tabela_dh())
    print("FK", cinematica_direta(0.0, 0.0, 0.0))
    print("URDF", sim.model_info())
    sim.conveyor_on(0.55)

    while sim.running and sim.placed < 4:
        sim.step()
        if sim.held is None:
            alvo = sim.next_object()
            if alvo is None:
                continue
            q1, q2, d3 = cinematica_inversa(alvo["x"], alvo["y"], alvo["z"])
            sim.move_joints(q1, q2, d3)
            if sim.can_pick():
                sim.pick()
        else:
            cesta = sim.basket_for(sim.held["color"])
            q1, q2, d3 = cinematica_inversa(cesta["x"], cesta["y"], 0.28)
            sim.move_joints(q1, q2, d3)
            if sim.can_place():
                sim.place()

    sim.export("scara_relatorio.csv")
    print("SCARA OK", sim.placed, sim.rejected)


def main():
    # The URDF tab is written beside the script by the worker.
    sim = ScaraSimulator("scara_cell.urdf")
    controlar(sim)


if __name__ == "__main__":
    main()
