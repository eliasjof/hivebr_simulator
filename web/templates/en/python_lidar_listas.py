"""Activity: cleaning LiDAR readings with lists.

The sensor returns distances in metres, but some are invalid (None, zero,
negative or infinite). Complete the functions to filter the list and summarise
the good readings. The console must print TUDO CERTO.
"""

import math

LEITURAS = [1.2, None, 0.0, 2.5, -1.0, 0.8, 3.4, float("inf"), 0.35]
DISTANCIA_MINIMA = 0.05
ALCANCE = 3.0


def validas(leituras):
    """Finite distances inside (DISTANCIA_MINIMA, ALCANCE]."""
    # TODO: use math.isfinite and compare with the limits.
    raise NotImplementedError


def distancia_minima(leituras):
    """Smallest valid distance, or None when there is none."""
    # TODO: use the list filtered by validas().
    raise NotImplementedError


def quantas_abaixo(leituras, limite):
    """How many valid readings are below the limit."""
    # TODO: count the valid readings smaller than the limit.
    raise NotImplementedError


def main():
    boas = validas(LEITURAS)
    minima = distancia_minima(LEITURAS)
    proximas = quantas_abaixo(LEITURAS, 1.0)

    assert boas == [1.2, 2.5, 0.8, 0.35]
    assert minima == 0.35
    assert proximas == 2

    print(f"Valid readings: {len(boas)}")
    print(f"Minimum distance: {minima:.2f} m")
    print(f"Readings below 1 m: {proximas}")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
