"""Activity: a ControladorPID class in pure Python.

The PID stores the accumulated error (integral) and the previous error
(derivative). Complete the update() method and watch the controller drive a
first-order plant to the target. The console must print TUDO CERTO.
"""


class ControladorPID:
    """Discrete PID with integral clamping."""

    def __init__(self, kp, ki, kd, limite_integral=1.0):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.limite_integral = float(limite_integral)
        self.integral = 0.0
        self.anterior = 0.0

    def update(self, erro, dt):
        """Return the PID output for the current error."""
        # TODO: accumulate integral += erro * dt, compute the derivative
        # (erro - self.anterior) / dt, apply the gains and clamp the integral.
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

    print(f"Final position: {posicao:.2f}")
    print(f"Integral: {pid.integral:.3f}")
    print("TUDO CERTO")


if __name__ == "__main__":
    main()
