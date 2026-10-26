from pathlib import Path
import sys
import pygame
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from hivebr.engine import Simulator, load_config
from examples.controllers.vortex_apf import vortex_apf_controller
from examples.controllers.potential_field import potential_field_force
from examples.controllers.potential_field import potential_field_controller


def draw_forces(sim, screen):

    goal = sim.waypoints.get_current_waypoint()

    forces = potential_field_force(
        sim.robot,
        goal,
        sim.config,
        sim.lidar_readings
    )

    f_att = forces["attractive"]
    f_rep = forces["repulsive"]
    f_tot = forces["total"]

    # posição do robô
    x, y = sim.robot.position
    start = sim.camera.world_to_screen(x, y)

    scale = 0.5  # ajuste visual

    # ==================================================
    # ATRATIVA (verde)
    # ==================================================
    end_att = sim.camera.world_to_screen(
        x + f_att[0] * scale,
        y + f_att[1] * scale
    )

    pygame.draw.line(screen, (0, 255, 0), start, end_att, 3)

    # ==================================================
    # REPULSIVA (vermelho)
    # ==================================================
    end_rep = sim.camera.world_to_screen(
        x + f_rep[0] * scale,
        y + f_rep[1] * scale
    )

    pygame.draw.line(screen, (255, 50, 50), start, end_rep, 3)

    # ==================================================
    # RESULTANTE (azul)
    # ==================================================
    end_tot = sim.camera.world_to_screen(
        x + f_tot[0] * scale,
        y + f_tot[1] * scale
    )

    pygame.draw.line(screen, (50, 150, 255), start, end_tot, 4)

    # ponto no robô
    pygame.draw.circle(screen, (255,255,255), start, 4)


# ======================================================
# FUNÇÃO DE DESENHO CUSTOMIZADA
# ======================================================


def custom_draw(sim, screen):
    draw_forces(sim, screen)
    draw_info(sim, screen)



# ======================================================
# DESENHAR CAMPO POTENCIAL
# ======================================================

def draw_heatmap(sim, screen):

    spacing = 0.3
    size = 6
    max_force = 5.0

    for x in np.arange(-5, 5, spacing):
        for y in np.arange(-5, 5, spacing):

            pos = np.array([x, y])

            # ✅ AGORA USA A FUNÇÃO CORRETA
            force = potential_field_force(
                sim.robot,
                sim.world,
                pos,
                sim.config,
                sim.lidar_readings
            )

            norm = np.linalg.norm(force)

            value = min(norm / max_force, 1.0)

            r = int(255 * value)
            g = int(50 * (1 - value))
            b = int(255 * (1 - value))

            color = (r, g, b)

            px, py = sim.camera.world_to_screen(x, y)

            rect = pygame.Rect(px, py, size, size)

            pygame.draw.rect(screen, color, rect)

def draw_vector_field(sim, screen):

    spacing = 1.0  # resolução do grid em unidades do mundo

    for x in np.arange(-5, 5, spacing):
        for y in np.arange(-5, 5, spacing):

            pos = np.array([x, y])

            # calcula força do mesmo controlador (sem mover o robô)
            force = sim.controller(
                sim.robot,
                sim.world,
                pos,
                sim.config,
                sim.dt,
                sim.lidar_readings
            )

            if "vx" in force:
                vec = np.array([force["vx"], force["vy"]])
            else:
                continue

            norm = np.linalg.norm(vec)

            if norm < 1e-3:
                continue

            dir_vec = vec / norm

            start = sim.camera.world_to_screen(x, y)
            end = sim.camera.world_to_screen(
                x + dir_vec[0] * 0.5,
                y + dir_vec[1] * 0.5
            )

            pygame.draw.line(screen, (0, 200, 255), start, end, 1)


# ======================================================
# DESENHAR TEXTO
# ======================================================

def draw_info(sim, screen):
    font = pygame.font.SysFont("consolas", 16)

    text = f"x={sim.robot.position[0]:.2f} y={sim.robot.position[1]:.2f}"

    surf = font.render(text, True, (255, 255, 255))
    screen.blit(surf, (20, 20))


# ======================================================
# MAIN
# ======================================================

if __name__ == "__main__":
    config = load_config(ROOT / "config" / "default.yaml")
    config["robot"]["type"] = "holonomic"

    sim = Simulator(
        config=config,
        controller=potential_field_controller,
        draw_callback=custom_draw  
    )

    sim.run()

