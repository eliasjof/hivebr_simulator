"""Atividade: supervisor de frota com listas e dicionarios.

Cada leitura e um dicionario com t (s), v (m/s), corrente (A) e bateria (%).
Complete as tres funcoes de analise e veja os testes imprimirem TUDO CERTO.
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
    """Media das velocidades registradas."""
    # TODO: some as velocidades e divida pela quantidade de leituras.
    raise NotImplementedError


def corrente_maxima(leituras):
    """Maior corrente registrada."""
    # TODO: use max() sobre o campo corrente.
    raise NotImplementedError


def alertas(leituras, limiar=50.0):
    """Quantidade de leituras com bateria abaixo do limiar."""
    # TODO: conte as leituras com bateria < limiar.
    raise NotImplementedError


def main():
    media = velocidade_media(LEITURAS)
    pico = corrente_maxima(LEITURAS)
    baixas = alertas(LEITURAS, 50.0)

    assert abs(media - 2.0 / 6.0) < 1e-9
    assert pico == 7.5
    assert baixas == 1

    print(f"Velocidade media: {media:.2f} m/s")
    print(f"Corrente maxima: {pico:.1f} A")
    print(f"Alertas de bateria: {baixas}")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
