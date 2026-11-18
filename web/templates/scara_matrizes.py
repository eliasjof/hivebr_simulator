"""Atividade: matrizes homogeneas do SCARA.

Cada linha da tabela DH vira uma matriz 4x4. Multiplique as tres matrizes e o
resultado deve colocar a ponta em (L1 + L2, 0, BASE_Z) quando todas as juntas
estao em zero.

Dicas:
  - Uma linha DH combina rotacao em Z (theta), translacao em Z (d),
    translacao em X (a) e rotacao em X (alpha).
  - Use multiplicar() para juntar as tres matrizes na ordem das juntas.

O script imprime MATRIZ OK no final.
"""

import math

from hivebr_web.scara import BASE_Z, L1, L2


def multiplicar(a, b):
    """Multiplica duas matrizes 4x4."""
    return [
        [sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]


def matriz_transformacao(theta, d, a, alpha):
    """Matriz homogenea 4x4 de uma linha DH (convencao classica)."""
    # TODO: monte a matriz com cos/sin de theta e alpha.
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def cinematica_direta(q1, q2, d3):
    """Devolve (x, y, z) da ponta para as juntas (q1, q2, d3)."""
    # TODO: use as tres linhas da tabela DH.
    t1 = matriz_transformacao(q1, BASE_Z, 0.0, 0.0)
    t2 = matriz_transformacao(q2, 0.0, L1, 0.0)
    t3 = matriz_transformacao(0.0, d3, L2, 0.0)
    t = multiplicar(multiplicar(t1, t2), t3)
    return t[0][3], t[1][3], t[2][3]


def conferir():
    """Devolve True quando as matrizes reproduzem a cinematica do SCARA."""
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
        print("Matrizes incorretas: revise theta, d, a e alpha.")


if __name__ == "__main__":
    main()
