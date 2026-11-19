"""Activity: describe the SCARA arm in URDF.

Open the scara_cell.urdf tab and fill the three origins marked with TODO. The
Python script reads exactly the same file that the simulation drawing uses, so
a wrong URDF makes the arm too short or too tall.

Hints:
  - The joint_1 origin Z is the shoulder height: 1.10 m.
  - The joint_2 origin X is the first arm: 1.60 m.
  - The joint_3 origin X is the second arm: 1.40 m.

The script prints URDF OK at the end.
"""

from hivebr_web.urdf import load_model, model_summary, tip


def conferir(modelo):
    """Returns True when the URDF describes the didactic SCARA."""
    esperado = {"l1": 1.6, "l2": 1.4, "base_z": 1.1}
    for chave, valor in esperado.items():
        if abs(float(modelo["lengths"][chave]) - valor) > 1e-6:
            return False
    tipos = [junta["type"] for junta in modelo["chain"]]
    if tipos != ["revolute", "revolute", "prismatic", "fixed"]:
        return False
    x, y, z = tip(modelo, {"q1": 0.0, "q2": 0.0, "d3": 0.0})
    if abs(x - 3.0) > 1e-6 or abs(y) > 1e-6 or abs(z - 1.1) > 1e-6:
        return False
    return True


def main():
    # The URDF tab is written beside the script by the worker.
    modelo = load_model("scara_cell.urdf")
    print("URDF", model_summary(modelo))
    if conferir(modelo):
        print("URDF OK")
    else:
        print("Incomplete URDF: review the origins of joints 1, 2 and 3.")


if __name__ == "__main__":
    main()
