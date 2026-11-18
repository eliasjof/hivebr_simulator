"""Activity: homogeneous matrices of the SCARA.

Each DH row becomes a 4x4 matrix. Multiply the three matrices and the result
must put the tip at (L1 + L2, 0, BASE_Z) when every joint is zero.

Hints:
  - A DH row combines a rotation around Z (theta), a translation along Z (d),
    a translation along X (a) and a rotation around X (alpha).
  - Use multiplicar() to combine the three matrices in joint order.

The script prints MATRIZ OK at the end.
"""

import math

from hivebr_web.scara import BASE_Z, L1, L2


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
    # TODO: use the three DH rows.
    t1 = matriz_transformacao(q1, BASE_Z, 0.0, 0.0)
    t2 = matriz_transformacao(q2, 0.0, L1, 0.0)
    t3 = matriz_transformacao(0.0, d3, L2, 0.0)
    t = multiplicar(multiplicar(t1, t2), t3)
    return t[0][3], t[1][3], t[2][3]


def conferir():
    """Returns True when the matrices reproduce the SCARA kinematics."""
    x, y, z = cinematica_direta(0.0, 0.0, 0.0)
    if abs(x - (L1 + L2)) > 1e-6 or abs(y) > 1e-6 or abs(z - BASE_Z) > 1e-6:
        return False
    x, y, z = cinematica_direta(math.pi / 2, 0.0, -0.2)
    if abs(x) > 1e-6 or abs(y - (L1 + L2)) > 1e-6 or abs(z - (BASE_Z - 0.2)) > 1e-6:
        return False
    return True


def main():
    if conferir():
        print("MATRIZ OK", cinematica_direta(0.0, 0.0, 0.0))
    else:
        print("Wrong matrices: review theta, d, a and alpha.")


if __name__ == "__main__":
    main()
