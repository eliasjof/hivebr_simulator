"""Atividade: tipos, operacoes e funcoes em Python.

Complete as tres funcoes abaixo. Os testes no final conferem o resultado e
imprimem TUDO CERTO quando tudo estiver correto.

Nao precisa mexer nos dados: use as listas DISTANCIAS e TEMPOS.
"""

DISTANCIAS = [1.2, 2.5, 3.8, 0.6, 4.1]  # metros
TEMPOS = [0.8, 1.5, 2.0, 0.4, 2.2]      # segundos


def distancia_total(distancias):
    """Devolve a soma das distancias percorridas."""
    # TODO: some todos os valores da lista.
    raise NotImplementedError


def velocidade_media(distancias, tempos):
    """Devolve a velocidade media em m/s (distancia total / tempo total)."""
    # TODO: use distancia_total e a soma dos tempos.
    raise NotImplementedError


def converter_kmh(velocidade_ms):
    """Converte uma velocidade de m/s para km/h."""
    # TODO: multiplique por 3.6.
    raise NotImplementedError


def main():
    total = distancia_total(DISTANCIAS)
    media = velocidade_media(DISTANCIAS, TEMPOS)
    kmh = converter_kmh(media)

    assert abs(total - 12.2) < 1e-9
    assert abs(media - 12.2 / 6.9) < 1e-9
    assert abs(kmh - (12.2 / 6.9) * 3.6) < 1e-9

    print(f"Distancia total: {total:.2f} m")
    print(f"Velocidade media: {media:.2f} m/s")
    print(f"Velocidade media: {kmh:.2f} km/h")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
