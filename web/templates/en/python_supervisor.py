"""Activity: fleet supervisor with lists and dictionaries.

Each reading is a dictionary with t (s), v (m/s), current (A) and battery (%).
Complete the three analysis functions and watch the tests print TUDO CERTO.
"""

LEITURAS = [
    {"t": 0.0, "v": 0.0, "corrente": 2.0, "bateria": 100.0},
    {"t": 1.0, "v": 0.4, "corrente": 5.0, "bateria": 92.0},
    {"t": 2.0, "v": 0.8, "corrente": 7.5, "bateria": 80.0},
    {"t": 3.0, "v": 0.6, "corrente": 6.0, "bateria": 68.0},
    {"t": 4.0, "v": 0.2, "corrente": 3.0, "bateria": 55.0},
    {"t": 5.0, "v": 0.0, "corrente": 2.0, "bateria": 40.0},
]


def velocidade_media(leituras):
    """Mean of the recorded speeds."""
    # TODO: sum the speeds and divide by the number of readings.
    raise NotImplementedError


def corrente_maxima(leituras):
    """Highest recorded current."""
    # TODO: use max() over the current field.
    raise NotImplementedError


def alertas(leituras, limiar=50.0):
    """Number of readings with battery below the threshold."""
    # TODO: count the readings with battery < threshold.
    raise NotImplementedError


def main():
    media = velocidade_media(LEITURAS)
    pico = corrente_maxima(LEITURAS)
    baixas = alertas(LEITURAS, 50.0)

    assert abs(media - 2.0 / 6.0) < 1e-9
    assert pico == 7.5
    assert baixas == 1

    print(f"Mean speed: {media:.2f} m/s")
    print(f"Peak current: {pico:.1f} A")
    print(f"Battery alerts: {baixas}")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
