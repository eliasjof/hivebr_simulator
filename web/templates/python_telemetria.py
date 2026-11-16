"""Atividade: telemetria de bateria de um robo de entrega.

A bateria tem CAPACIDADE_WH e o robo consome CONSUMO_W. Complete as duas
funcoes: autonomia_horas() devolve quantas horas a bateria dura e
tempo_ate_alerta() devolve o primeiro instante em que a carga fica abaixo do
limiar (ou None se isso nunca acontecer).

O grafico da descarga e salvo em autonomia.png e o console deve mostrar
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
    """Duracao da bateria em horas."""
    # TODO: divida a capacidade pelo consumo.
    raise NotImplementedError


def tempo_ate_alerta(amostras, limiar=LIMIAR):
    """Primeiro instante (s) com bateria <= limiar, ou None."""
    # TODO: percorra as amostras e devolva o primeiro t que satisfaz a condicao.
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

    print(f"Autonomia: {horas:.2f} h")
    print(f"Alerta em {alerta} s")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
