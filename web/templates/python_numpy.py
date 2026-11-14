"""Atividade: NumPy, arrays e matrizes de rotacao.

Monte a matriz de rotacao 2D, aplique-a a um vetor e plote o resultado.
Os testes conferem a matematica; a figura e a entrega visual da atividade.
"""

import numpy as np
import matplotlib.pyplot as plt


def matriz_rotacao(theta):
    """Devolve a matriz 2x2 que gira um vetor em theta radianos."""
    # TODO: monte [[cos, -sin], [sin, cos]] com np.cos e np.sin.
    raise NotImplementedError


def rotacionar(pontos, theta):
    """Gira uma lista de pontos (N, 2) em torno da origem."""
    # TODO: use a matriz de rotacao. Lembre que pontos @ R.T funciona.
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

    print(f"Matriz de rotacao:\n{R}")
    print(f"Media da coordenada x: {np.mean(pontos[:, 0]):.2f}")
    print(f"Desvio padrao da coordenada x: {np.std(pontos[:, 0]):.2f}")

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
