"""Atividade: descrever o braco SCARA no URDF.

Abra a aba scara_cell.urdf e preencha os tres origins marcados com TODO. O
Python le exatamente o mesmo arquivo que o desenho da simulacao usa, entao um
URDF errado deixa o braco curto ou alto demais.

Dicas:
  - O origin da joint_1 em Z e a altura do ombro: 0,80 m.
  - O origin da joint_2 em X e o primeiro braco: 1,60 m.
  - O origin da joint_3 em X e o segundo braco: 1,40 m.

O script imprime URDF OK no final.
"""

from hivebr_web.urdf import load_model, model_summary, tip


def conferir(modelo):
    """Devolve True quando o URDF descreve o SCARA didatico."""
    esperado = {"l1": 1.6, "l2": 1.4, "base_z": 0.8}
    for chave, valor in esperado.items():
        if abs(float(modelo["lengths"][chave]) - valor) > 1e-6:
            return False
    tipos = [junta["type"] for junta in modelo["chain"]]
    if tipos != ["revolute", "revolute", "prismatic", "fixed"]:
        return False
    x, y, z = tip(modelo, {"q1": 0.0, "q2": 0.0, "d3": 0.0})
    if abs(x - 3.0) > 1e-6 or abs(y) > 1e-6 or abs(z - 0.8) > 1e-6:
        return False
    return True


def main():
    # A aba do URDF e gravada ao lado do script pelo worker.
    modelo = load_model("scara_cell.urdf")
    print("URDF", model_summary(modelo))
    if conferir(modelo):
        print("URDF OK")
    else:
        print("URDF incompleto: revise os origins das juntas 1, 2 e 3.")


if __name__ == "__main__":
    main()
