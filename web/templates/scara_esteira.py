"""Atividade: celula SCARA com esteira, deteccao de cor e cestas.

A esteira traz pecas vermelhas, verdes e azuis. O braco SCARA de 3 juntas
(q1, q2 e a prismatica d3) deve pegar cada peca e colocar na cesta da mesma
cor. O simulador entrega a posicao das pecas; a cinematica e sua.

Complete, nesta ordem:
  1. tabela_dh(): a tabela de Denavit-Hartenberg do SCARA.
  2. matriz_transformacao(): a matriz homogenea 4x4 de uma linha DH.
  3. cinematica_direta(): multiplica as matrizes e devolve (x, y, z).
  4. cinematica_inversa(): lei dos cossenos para achar (q1, q2, d3).

O arquivo scara_cell.urdf tambem faz parte da atividade: ele define a altura
do ombro e os dois comprimentos do braco. Se o URDF estiver errado, o robo nao
alcanca a esteira. Preencha os TODO do URDF antes de rodar.

Dicas:
  - O alcance e L1 + L2 = 3,0 m; a base fica em BASE_Z (1,10 m).
  - Use math.atan2(y, x) e math.acos() com o argumento limitado a [-1, 1].
  - O eletroima e a ponta: alvo["z"] e o topo da peca e a garra desce ate la.
  - Entre um alvo e outro, o braco sobe para TRANSIT_Z antes de viajar.

O script imprime SCARA OK no final e grava scara_relatorio.csv.
"""

import math

from hivebr_web.scara import BASE_Z, BASKET_Z, L1, L2, TRANSIT_Z, ScaraSimulator


def tabela_dh():
    """Tabela DH do SCARA: uma linha por junta.

    Cada linha tem theta, d, a e alpha. Troque os textos pelos valores
    numericos ou pelas variaveis de junta.
    """
    # TODO: preencha a tabela DH do SCARA.
    return [
        {"theta": "q1", "d": "d1", "a": "a1", "alpha": "alpha1"},
        {"theta": "q2", "d": "d2", "a": "a2", "alpha": "alpha2"},
        {"theta": "0", "d": "d3", "a": "a3", "alpha": "alpha3"},
    ]


def multiplicar(a, b):
    """Multiplica duas matrizes 4x4."""
    return [
        [sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]


def matriz_transformacao(theta, d, a, alpha):
    """Matriz homogenea 4x4 de uma linha DH (convencao classica)."""
    # TODO: monte a matriz com cos/sin de theta e alpha.
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def cinematica_direta(q1, q2, d3):
    """Devolve (x, y, z) da ponta para as juntas (q1, q2, d3)."""
    # TODO: use tabela_dh() e matriz_transformacao().
    t1 = matriz_transformacao(q1, BASE_Z, 0.0, 0.0)
    t2 = matriz_transformacao(q2, 0.0, L1, 0.0)
    t3 = matriz_transformacao(0.0, d3, L2, 0.0)
    t = multiplicar(multiplicar(t1, t2), t3)
    return t[0][3], t[1][3], t[2][3]


def cinematica_inversa(x, y, z):
    """Devolve (q1, q2, d3) para a ponta em (x, y, z)."""
    # TODO: lei dos cossenos para q2 e atan2 para q1.
    return 0.0, 0.0, 0.0


def distancia_xy(sim, x, y):
    """Distancia horizontal entre a ponta e o alvo."""
    px, py, _ = sim.tip()
    return math.hypot(px - x, py - y)


def ir_para(sim, x, y, z):
    """Calcula a IK do alvo e atualiza as juntas."""
    q1, q2, d3 = cinematica_inversa(x, y, z)
    sim.move_joints(q1, q2, d3)


def controlar(sim):
    """Laco principal: esteira, deteccao de cor, pega e coloca."""
    print("DH", tabela_dh())
    print("FK", cinematica_direta(0.0, 0.0, 0.0))
    print("URDF", sim.model_info())
    sim.conveyor_on(0.55)

    while sim.running and sim.placed < 4:
        sim.step()
        if sim.held is None:
            # sim.detect() lista as leituras do sensor; cada uma tem "color".
            alvo = sim.next_object()
            if alvo is None:
                continue
            # Primeiro va acima da peca; o eletroima desce so no final.
            if distancia_xy(sim, alvo["x"], alvo["y"]) > 0.15:
                ir_para(sim, alvo["x"], alvo["y"], TRANSIT_Z)
                continue
            # alvo["z"] e o topo da peca: desca ate encostar.
            ir_para(sim, alvo["x"], alvo["y"], alvo["z"])
            if sim.can_pick():
                # alvo["color"] e a cor detectada: "red", "green" ou "blue".
                print("Cor detectada:", alvo["color"])
                sim.pick()
        else:
            cesta = sim.basket_for(sim.held["color"])
            # Suba com a peca antes de viajar ate a cesta.
            if distancia_xy(sim, cesta["x"], cesta["y"]) > 0.15:
                ir_para(sim, cesta["x"], cesta["y"], TRANSIT_Z)
                continue
            ir_para(sim, cesta["x"], cesta["y"], BASKET_Z)
            if sim.can_place():
                sim.place()

    sim.export("scara_relatorio.csv")
    print("SCARA OK", sim.placed, sim.rejected)


def main():
    # The URDF tab is written beside the script by the worker.
    sim = ScaraSimulator("scara_cell.urdf")
    controlar(sim)


if __name__ == "__main__":
    main()
