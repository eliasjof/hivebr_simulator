"""Activity: Python types, operations and functions.

Complete the three functions below. The tests at the end check the result and
print TUDO CERTO when everything is correct.

Do not change the data: use the DISTANCIAS and TEMPOS lists.
"""

DISTANCIAS = [1.2, 2.5, 3.8, 0.6, 4.1]  # meters
TEMPOS = [0.8, 1.5, 2.0, 0.4, 2.2]      # seconds


def distancia_total(distancias):
    """Return the sum of the travelled distances."""
    # TODO: add every value in the list.
    raise NotImplementedError


def velocidade_media(distancias, tempos):
    """Return the average speed in m/s (total distance / total time)."""
    # TODO: use distancia_total and the sum of the times.
    raise NotImplementedError


def converter_kmh(velocidade_ms):
    """Convert a speed from m/s to km/h."""
    # TODO: multiply by 3.6.
    raise NotImplementedError


def main():
    total = distancia_total(DISTANCIAS)
    media = velocidade_media(DISTANCIAS, TEMPOS)
    kmh = converter_kmh(media)

    assert abs(total - 12.2) < 1e-9
    assert abs(media - 12.2 / 6.9) < 1e-9
    assert abs(kmh - (12.2 / 6.9) * 3.6) < 1e-9

    print(f"Total distance: {total:.2f} m")
    print(f"Average speed: {media:.2f} m/s")
    print(f"Average speed: {kmh:.2f} km/h")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
