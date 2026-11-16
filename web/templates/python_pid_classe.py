"""Atividade: uma classe ControladorPID em Python puro.

O PID guarda o erro acumulado (integral) e o erro anterior (derivada). Complete
o metodo update() e veja o controlador levar uma planta de primeira ordem ate o
alvo. O console deve mostrar TUDO CERTO.
"""


class ControladorPID:
    """PID discreto com limite no termo integral."""

    def __init__(self, kp, ki, kd, limite_integral=1.0):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.limite_integral = float(limite_integral)
        self.integral = 0.0
        self.anterior = 0.0

    def update(self, erro, dt):
        """Devolve a saida do PID para o erro atual."""
        # TODO: acumule integral += erro * dt, calcule a derivada
        # (erro - self.anterior) / dt, aplique os ganhos e limite o integral.
        raise NotImplementedError


def main():
    pid = ControladorPID(1.2, 0.4, 0.05, 1.0)
    alvo = 10.0
    posicao = 0.0
    dt = 0.05
    for _ in range(400):
        erro = alvo - posicao
        velocidade = pid.update(erro, dt)
        posicao += velocidade * dt

    assert abs(posicao - alvo) < 0.2
    assert abs(pid.integral) <= pid.limite_integral + 1e-9

    print(f"Posicao final: {posicao:.2f}")
    print(f"Integral: {pid.integral:.3f}")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
