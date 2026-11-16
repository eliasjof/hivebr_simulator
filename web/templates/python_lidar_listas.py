"""Atividade: limpeza de leituras do LiDAR com listas.

O sensor devolve distancias em metros, mas algumas sao invalidas (None, zero,
negativas ou infinitas). Complete as funcoes para filtrar a lista e resumir as
leituras boas. O console deve mostrar TUDO CERTO.
"""

import math

LEITURAS = [1.2, None, 0.0, 2.5, -1.0, 0.8, 3.4, float("inf"), 0.35]
DISTANCIA_MINIMA = 0.05
ALCANCE = 3.0


def validas(leituras):
    """Distancias finitas dentro de (DISTANCIA_MINIMA, ALCANCE]."""
    # TODO: use math.isfinite e compare com os limites.
    raise NotImplementedError


def distancia_minima(leituras):
    """Menor distancia valida, ou None quando nao ha nenhuma."""
    # TODO: use a lista filtrada por validas().
    raise NotImplementedError


def quantas_abaixo(leituras, limite):
    """Quantas leituras validas ficam abaixo do limite."""
    # TODO: conte as leituras validas menores que o limite.
    raise NotImplementedError


def main():
    boas = validas(LEITURAS)
    minima = distancia_minima(LEITURAS)
    proximas = quantas_abaixo(LEITURAS, 1.0)

    assert boas == [1.2, 2.5, 0.8, 0.35]
    assert minima == 0.35
    assert proximas == 2

    print(f"Leituras validas: {len(boas)}")
    print(f"Distancia minima: {minima:.2f} m")
    print(f"Leituras abaixo de 1 m: {proximas}")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
