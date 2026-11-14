"""Atividade: plotando uma trajetoria com matplotlib.

Implemente trajetoria(t), plote a curva com rotulos e legenda e salve o
arquivo trajetoria.png. A figura e o arquivo sao a entrega da atividade.
"""

import numpy as np
import matplotlib.pyplot as plt


def trajetoria(t):
    """Devolve (x, y) da lemniscata para um array de tempos t.

    Use x = 3 * cos(t) e y = 1.5 * sin(2t).
    """
    # TODO: implemente as duas coordenadas.
    raise NotImplementedError


def main():
    t = np.linspace(0.0, 2.0 * np.pi, 400)
    x, y = trajetoria(t)

    assert np.allclose(trajetoria(0.0), trajetoria(2.0 * np.pi))
    assert np.isclose(np.max(np.abs(x)), 3.0)

    print(f"Pontos plotados: {len(t)}")
    print(f"x entre {x.min():.2f} e {x.max():.2f}")
    print(f"y entre {y.min():.2f} e {y.max():.2f}")

    plt.figure(figsize=(6, 4))
    plt.plot(x, y, label="trajectory")
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    plt.title("Parametric trajectory")
    plt.axis("equal")
    plt.grid(True)
    plt.legend()
    plt.savefig("trajetoria.png")
    plt.show()
    print("FIGURA SALVA")


if __name__ == "__main__":
    main()
