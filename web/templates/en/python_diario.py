"""Activity: CSV logbook.

The robot recorded telemetry in a list of dictionaries. Complete
salvar_diario() to write the file diario.csv with the header t,x,y,v and one
line per reading. The console must print TUDO CERTO.
"""

from pathlib import Path

LINHAS = [
    {"t": 0.0, "x": 2.0, "y": 2.0, "v": 0.0},
    {"t": 1.0, "x": 2.4, "y": 2.0, "v": 0.4},
    {"t": 2.0, "x": 2.8, "y": 2.1, "v": 0.4},
    {"t": 3.0, "x": 3.2, "y": 2.2, "v": 0.4},
]
CABECALHO = "t,x,y,v"


def salvar_diario(linhas, caminho="diario.csv"):
    """Write the lines in CSV format with two decimal places."""
    # TODO: open the file with Path(caminho).open("w", encoding="utf-8"),
    # write the header and then one line per reading.
    raise NotImplementedError


def main():
    caminho = Path("diario.csv")
    if caminho.exists():
        caminho.unlink()
    salvar_diario(LINHAS)

    assert caminho.exists()
    texto = caminho.read_text(encoding="utf-8")
    linhas = texto.strip().splitlines()
    assert linhas[0] == CABECALHO
    assert len(linhas) == len(LINHAS) + 1
    assert linhas[1].split(",")[0] == "0.00"

    print(f"Lines written: {len(linhas) - 1}")
    print(f"File: {caminho}")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
