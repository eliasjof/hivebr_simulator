"""Atividade: tabela de Denavit-Hartenberg do braco SCARA.

A tabela DH tem uma linha por junta, com theta, d, a e alpha. Preencha as
tres linhas do SCARA didatico (q1, q2 e a prismatica d3) e rode o script: a
verificacao imprime DH OK quando a tabela bate com o URDF.

Dicas:
  - A altura do ombro e BASE_Z (1,10 m): ela fica no d da junta 1.
  - Os bracos medem L1 (1,60 m) e L2 (1,40 m): eles ficam no a.
  - Apenas as duas primeiras juntas giram; a junta 3 desliza em Z.

O script imprime DH OK no final.
"""

from hivebr_web.scara import BASE_Z, L1, L2


def tabela_dh():
    """Uma linha DH por junta: theta, d, a e alpha."""
    # TODO: preencha as tres linhas. Use "q1", "q2" e "d3" para as variaveis
    # de junta e numeros para as dimensoes fixas.
    return [
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
    ]


def numero(valor):
    """Converte "q1"/"d3" em texto e numeros em floats arredondados."""
    if isinstance(valor, str):
        texto = valor.strip().lower()
        try:
            return round(float(texto), 6)
        except ValueError:
            return texto
    return round(float(valor), 6)


def conferir(tabela):
    """Devolve True quando a tabela e a do SCARA."""
    esperado = [
        {"theta": "q1", "d": round(BASE_Z, 6), "a": 0.0, "alpha": 0.0},
        {"theta": "q2", "d": 0.0, "a": round(L1, 6), "alpha": 0.0},
        {"theta": 0.0, "d": "d3", "a": round(L2, 6), "alpha": 0.0},
    ]
    if len(tabela) != len(esperado):
        return False
    for linha, alvo in zip(tabela, esperado):
        for chave in ("theta", "d", "a", "alpha"):
            if numero(linha.get(chave)) != alvo[chave]:
                return False
    return True


def main():
    tabela = tabela_dh()
    if conferir(tabela):
        print("DH OK", tabela)
    else:
        print("Tabela DH incorreta: revise theta, d, a e alpha.")


if __name__ == "__main__":
    main()
