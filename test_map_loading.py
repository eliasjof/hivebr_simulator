# import numpy as np
# from PIL import Image
# import os

# # Create a dummy maze image (100x100)
# # White background, black walls
# img = Image.new("L", (100, 100), 255)
# # Draw a rectangle border
# for i in range(100):
#     img.putpixel((0, i), 0)
#     img.putpixel((99, i), 0)
#     img.putpixel((i, 0), 0)
#     img.putpixel((i, 99), 0)
# # Draw a wall in the middle
# for i in range(20, 80):
#     img.putpixel((i, 50), 0)

# img.save("maze.png")
# print("Image 'maze.png' created.")

# # Test the OccupancyGridMap logic
# from hivebr.engine.occupancy_grid import OccupancyGridMap

# try:
#     # 100 pixels * 0.1 m/pixel = 10m x 10m map
#     grid_map = OccupancyGridMap("maze.png", resolution=0.1, robot_radius=0.2)
    
#     print(f"Map loaded successfully!")
#     print(f"Grid shape: {grid_map.grid.shape}")
#     print(f"World dimensions: {grid_map.width_m}m x {grid_map.height_m}m")
    
#     # Check a point known to be free (center is at (50,50) in pixels -> world coords depends on resolution)
#     # The image is 100x100, 0.1m/pixel, so (50,50) in image is (5.0, 5.0) in world
#     # Let's test a point that should be free
#     is_occ = grid_map.is_occupied(5.0, 2.0, use_inflated=False)
#     print(f"Point (5.0, 2.0) occupied: {is_occ}")
    
#     # Test a point known to be occupied (the border)
#     is_occ_wall = grid_map.is_occupied(0.05, 0.05, use_inflated=False)
#     print(f"Point (0.05, 0.05) [wall] occupied: {is_occ_wall}")

# except Exception as e:
#     print(f"Error during test: {e}")

import numpy as np
from PIL import Image, ImageDraw

# ============================================
# Configuração
# ============================================

world_width_m = 20
world_height_m = 20

pixels_per_meter = 10

W = int(world_width_m * pixels_per_meter)
H = int(world_height_m * pixels_per_meter)

# branco = livre
img = Image.new("L", (W, H), 255)
draw = ImageDraw.Draw(img)

# ============================================
# Bordas
# ============================================

draw.rectangle([0, 0, W-1, H-1], outline=0, width=3)

# ============================================
# Obstáculos internos
# ============================================

# Parede vertical esquerda
draw.rectangle([40, 20, 50, 150], fill=0)

# Parede vertical direita
draw.rectangle([140, 50, 150, 180], fill=0)

# Parede horizontal superior
draw.rectangle([60, 40, 170, 50], fill=0)

# Parede horizontal inferior
draw.rectangle([20, 140, 130, 150], fill=0)

# Bloco central
draw.rectangle([85, 80, 115, 120], fill=0)

# Pequenos obstáculos
draw.rectangle([30, 170, 50, 190], fill=0)
draw.rectangle([160, 20, 180, 40], fill=0)
draw.rectangle([170, 120, 190, 140], fill=0)

# ============================================
# Salva
# ============================================

img.save("maze2.png")

print("Mapa salvo em maze20x20.png")