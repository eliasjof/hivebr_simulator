"""Activity: plotting a trajectory with matplotlib.

Implement trajetoria(t), plot the curve with labels and a legend and save the
file trajetoria.png. The figure and the file are the deliverables.
"""

import numpy as np
import matplotlib.pyplot as plt


def trajetoria(t):
    """Return (x, y) of the lemniscate for an array of times t.

    Use x = 3 * cos(t) and y = 1.5 * sin(2t).
    """
    # TODO: implement both coordinates.
    raise NotImplementedError


def main():
    t = np.linspace(0.0, 2.0 * np.pi, 400)
    x, y = trajetoria(t)

    assert np.allclose(trajetoria(0.0), trajetoria(2.0 * np.pi))
    assert np.isclose(np.max(np.abs(x)), 3.0)

    print(f"Plotted points: {len(t)}")
    print(f"x from {x.min():.2f} to {x.max():.2f}")
    print(f"y from {y.min():.2f} to {y.max():.2f}")

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
