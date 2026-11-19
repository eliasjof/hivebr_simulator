"""Solução de referência do professor — célula SCARA com esteira (nível 5).

Este arquivo NÃO é publicado na web: ele fica fora de web/templates e fora do
catálogo de exemplos, portanto não entra no build do HiveBr Web. Use-o apenas
para conferir as respostas das atividades `scara-dh`, `scara-matrizes`,
`scara-urdf` e `scara-esteira`.

Como rodar fora do navegador:

    cd web/python
    PYTHONPATH=. python ../../professor/scara/scara_esteira_resolvido.py

O script usa o URDF resolvido que está ao lado dele
(`scara_cell_resolvido.urdf`), imprime as leituras de cor e grava
`scara_relatorio.csv` no diretório atual.

Respostas que o aluno deve produzir:
  1. Tabela DH:
       {"theta": "q1", "d": BASE_Z, "a": 0.0, "alpha": 0.0}
       {"theta": "q2", "d": 0.0,    "a": L1,   "alpha": 0.0}
       {"theta": 0.0,  "d": "d3",   "a": L2,   "alpha": 0.0}
  2. Matriz homogênea clássica (linha DH):
       [[ct, -st*ca,  st*sa, a*ct],
        [st,  ct*ca, -ct*sa, a*st],
        [0.0,    sa,     ca,    d],
        [0.0,   0.0,    0.0,  1.0]]
  3. Cinemática inversa:
       c2 = (x² + y² - L1² - L2²) / (2*L1*L2), limitado a [-1, 1]
       q2 = acos(c2)
       q1 = atan2(y, x) - atan2(L2*sen(q2), L1 + L2*cos(q2))
       d3 = z - BASE_Z
  4. URDF: joint_1 em z = 1.10, joint_2 em x = 1.60, joint_3 em x = 1.40.
     O ponto de ferramenta é a face inferior do eletroímã (z = 0 local).

O laço sobe para TRANSIT_Z entre alvos, desce até o topo da peça, pega, sobe,
viaja até a cesta, desce até BASKET_Z e solta. Assim a garra eletromagnética
aparece descendo e subindo em cada ciclo.
"""

import math
import os

from hivebr_web.scara import BASE_Z, BASKET_Z, L1, L2, TRANSIT_Z, ScaraSimulator

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scara_cell_resolvido.urdf")


def tabela_dh():
    """Tabela DH resolvida do SCARA (uma linha por junta)."""
    return [
        {"theta": "q1", "d": BASE_Z, "a": 0.0, "alpha": 0.0},
        {"theta": "q2", "d": 0.0, "a": L1, "alpha": 0.0},
        {"theta": 0.0, "d": "d3", "a": L2, "alpha": 0.0},
    ]


def multiplicar(a, b):
    """Multiplica duas matrizes 4x4."""
    return [
        [sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]


def matriz_transformacao(theta, d, a, alpha):
    """Matriz homogênea 4x4 de uma linha DH (convenção clássica)."""
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return [
        [ct, -st * ca, st * sa, a * ct],
        [st, ct * ca, -ct * sa, a * st],
        [0.0, sa, ca, d],
        [0.0, 0.0, 0.0, 1.0],
    ]


def cinematica_direta(q1, q2, d3):
    """Devolve (x, y, z) da ponta para as juntas (q1, q2, d3)."""
    t1 = matriz_transformacao(q1, BASE_Z, 0.0, 0.0)
    t2 = matriz_transformacao(q2, 0.0, L1, 0.0)
    t3 = matriz_transformacao(0.0, d3, L2, 0.0)
    t = multiplicar(multiplicar(t1, t2), t3)
    return t[0][3], t[1][3], t[2][3]


def cinematica_inversa(x, y, z):
    """Devolve (q1, q2, d3) para a ponta em (x, y, z)."""
    r2 = x * x + y * y
    c2 = (r2 - L1 * L1 - L2 * L2) / (2.0 * L1 * L2)
    c2 = max(-1.0, min(1.0, c2))
    q2 = math.acos(c2)
    q1 = math.atan2(y, x) - math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    d3 = z - BASE_Z
    return q1, q2, d3


def distancia_xy(sim, x, y):
    """Distância horizontal entre a ponta e o alvo."""
    px, py, _ = sim.tip()
    return math.hypot(px - x, py - y)


def ir_para(sim, x, y, z):
    """Calcula a IK do alvo e atualiza as juntas."""
    q1, q2, d3 = cinematica_inversa(x, y, z)
    sim.move_joints(q1, q2, d3)


def controlar(sim):
    """Laço principal: esteira, detecção de cor, pega e coloca."""
    print("DH", tabela_dh())
    print("FK", cinematica_direta(0.0, 0.0, 0.0))
    print("URDF", sim.model_info())
    sim.conveyor_on(0.55)

    while sim.running and sim.placed < 4:
        sim.step()
        if sim.held is None:
            alvo = sim.next_object()
            if alvo is None:
                continue
            # Primeiro va acima da peça; o eletroímã desce só no final.
            if distancia_xy(sim, alvo["x"], alvo["y"]) > 0.15:
                ir_para(sim, alvo["x"], alvo["y"], TRANSIT_Z)
                continue
            # alvo["z"] é o topo da peça: desça até encostar.
            ir_para(sim, alvo["x"], alvo["y"], alvo["z"])
            if sim.can_pick():
                # A cor vem do sensor do simulador: "red", "green" ou "blue".
                print("Cor detectada:", alvo["color"])
                sim.pick()
        else:
            cesta = sim.basket_for(sim.held["color"])
            # Suba com a peça antes de viajar até a cesta.
            if distancia_xy(sim, cesta["x"], cesta["y"]) > 0.15:
                ir_para(sim, cesta["x"], cesta["y"], TRANSIT_Z)
                continue
            ir_para(sim, cesta["x"], cesta["y"], BASKET_Z)
            if sim.can_place():
                sim.place()

    sim.export("scara_relatorio.csv")
    print("SCARA OK", sim.placed, sim.rejected)


def main():
    sim = ScaraSimulator(model_path=MODEL)
    controlar(sim)


if __name__ == "__main__":
    main()
