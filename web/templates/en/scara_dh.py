"""Activity: Denavit-Hartenberg table of the SCARA arm.

The DH table has one row per joint, with theta, d, a and alpha. Fill the
three rows of the didactic SCARA (q1, q2 and the prismatic d3) and run the
script: the check prints DH OK when the table matches the URDF.

Hints:
  - The shoulder height is BASE_Z (0.80 m): it belongs to d of joint 1.
  - The arms measure L1 (1.60 m) and L2 (1.40 m): they belong to a.
  - Only the first two joints rotate; joint 3 slides along Z.

The script prints DH OK at the end.
"""

from hivebr_web.scara import BASE_Z, L1, L2


def tabela_dh():
    """One DH row per joint: theta, d, a and alpha."""
    # TODO: fill the three rows. Use "q1", "q2" and "d3" for the joint
    # variables and numbers for the fixed dimensions.
    return [
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
        {"theta": "?", "d": "?", "a": "?", "alpha": "?"},
    ]


def numero(valor):
    """Turns "q1"/"d3" into text and numbers into rounded floats."""
    if isinstance(valor, str):
        texto = valor.strip().lower()
        try:
            return round(float(texto), 6)
        except ValueError:
            return texto
    return round(float(valor), 6)


def conferir(tabela):
    """Returns True when the table is the SCARA table."""
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
        print("Wrong DH table: review theta, d, a and alpha.")


if __name__ == "__main__":
    main()
