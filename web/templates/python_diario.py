"""Atividade: diario de bordo em CSV.

O robo registrou a telemetria em uma lista de dicionarios. Complete
salvar_diario() para gravar o arquivo diario.csv com o cabecalho t,x,y,v e uma
linha por leitura. O console deve mostrar TUDO CERTO.
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
    """Grava as linhas no formato CSV com duas casas decimais."""
    # TODO: abra o arquivo com Path(caminho).open("w", encoding="utf-8"),
    # escreva o cabecalho e depois uma linha por leitura.
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

    print(f"Linhas gravadas: {len(linhas) - 1}")
    print(f"Arquivo: {caminho}")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
