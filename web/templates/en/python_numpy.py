"""Activity: NumPy, arrays and rotation matrices.

Build the 2D rotation matrix, apply it to a vector and plot the result.
The tests check the math; the figure is the visual deliverable.
"""

import numpy as np
import matplotlib.pyplot as plt


def matriz_rotacao(theta):
    """Return the 2x2 matrix that rotates a vector by theta radians."""
    # TODO: build [[cos, -sin], [sin, cos]] with np.cos and np.sin.
    raise NotImplementedError


def rotacionar(pontos, theta):
    """Rotate a list of points (N, 2) around the origin."""
    # TODO: use the rotation matrix. Remember that pontos @ R.T works.
    raise NotImplementedError


def main():
    R = matriz_rotacao(np.pi / 2.0)
    assert R is not None
    assert R.shape == (2, 2)
    assert np.allclose(R @ np.array([1.0, 0.0]), [0.0, 1.0])

    pontos = np.array([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
    girados = rotacionar(pontos, np.pi / 2.0)
    assert girados is not None
    assert np.allclose(girados, [[0.0, 1.0], [0.0, 2.0], [0.0, 3.0]])

    print(f"Rotation matrix:\n{R}")
    print(f"Mean x coordinate: {np.mean(pontos[:, 0]):.2f}")
    print(f"Std x coordinate: {np.std(pontos[:, 0]):.2f}")

    plt.figure(figsize=(5, 5))
    plt.plot(pontos[:, 0], pontos[:, 1], "o-", label="before")
    plt.plot(girados[:, 0], girados[:, 1], "s-", label="after")
    plt.axhline(0, color="gray", linewidth=0.8)
    plt.axvline(0, color="gray", linewidth=0.8)
    plt.axis("equal")
    plt.grid(True)
    plt.legend()
    plt.title("Rotation 90 deg")
    plt.show()
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
