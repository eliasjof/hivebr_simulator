"""Activity: battery telemetry for a delivery robot.

The battery has CAPACIDADE_WH and the robot draws CONSUMO_W. Complete the two
functions: autonomia_horas() returns how many hours the battery lasts and
tempo_ate_alerta() returns the first instant the charge falls below the
threshold (or None if that never happens).

The discharge plot is saved to autonomia.png and the console must print
TUDO CERTO.
"""

import matplotlib.pyplot as plt

CAPACIDADE_WH = 120.0
CONSUMO_W = 18.0
LIMIAR = 20.0

AMOSTRAS = [
    (0, 100.0),
    (600, 82.0),
    (1200, 64.0),
    (1800, 46.0),
    (2400, 28.0),
    (3000, 10.0),
]


def autonomia_horas(capacidade_wh, consumo_w):
    """Battery duration in hours."""
    # TODO: divide the capacity by the consumption.
    raise NotImplementedError


def tempo_ate_alerta(amostras, limiar=LIMIAR):
    """First instant (s) with battery <= threshold, or None."""
    # TODO: walk the samples and return the first t that satisfies the condition.
    raise NotImplementedError


def main():
    horas = autonomia_horas(CAPACIDADE_WH, CONSUMO_W)
    alerta = tempo_ate_alerta(AMOSTRAS, LIMIAR)

    assert abs(horas - CAPACIDADE_WH / CONSUMO_W) < 1e-9
    assert alerta == 3000

    tempos = [amostra[0] / 60.0 for amostra in AMOSTRAS]
    cargas = [amostra[1] for amostra in AMOSTRAS]

    plt.figure(figsize=(6, 4))
    plt.plot(tempos, cargas, "o-", label="battery")
    plt.axhline(LIMIAR, color="red", linestyle="--", label="alert")
    plt.xlabel("time (min)")
    plt.ylabel("charge (%)")
    plt.title("Battery telemetry")
    plt.grid(True)
    plt.legend()
    plt.savefig("autonomia.png")
    plt.show()

    print(f"Range: {horas:.2f} h")
    print(f"Alert at {alerta} s")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
