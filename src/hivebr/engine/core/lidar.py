from __future__ import annotations
import math
import numpy as np


class Lidar:
    def __init__(self, config: dict):
        c = config["lidar"]
        self.enabled = bool(c.get("enabled", True))
        self.num_rays = int(c.get("num_rays", 41))
        self.range = float(c.get("range", 4.0))
        self.fov = math.radians(float(c.get("fov_deg", 180)))
        self.colors = config["colors"]

    def ray_circle_intersection(self, ray_origin, ray_dir, obs):
        circle_radius = obs[2]
        circle_center = np.array(obs[:2])
        oc = ray_origin - circle_center
        a = np.dot(ray_dir, ray_dir)
        b = 2.0 * np.dot(oc, ray_dir)
        c = np.dot(oc, oc) - circle_radius ** 2
        disc = b*b - 4*a*c
        if disc < 0:
            return None
        sq = math.sqrt(disc)
        valid = [t for t in [(-b - sq)/(2*a), (-b + sq)/(2*a)] if 0 <= t <= self.range]
        return min(valid) if valid else None

    def cast_rays(self, robot, world, other_robots=None):
        """Faz ray-casting a partir de ``robot``.

        ``other_robots`` permite tratar os demais B-bots como obstáculos
        móveis (círculos com o raio do robô). Passe ``None`` para ignorá-los.
        """
        readings = []
        angles = np.linspace(robot.theta - self.fov/2, robot.theta + self.fov/2, self.num_rays)
        
        # Check if grid map exists for ray casting
        grid_map = getattr(world, 'grid_map', None)

        # Círculos dos demais robôs (obstáculos móveis).
        robot_circles = []
        if other_robots:
            for other in other_robots:
                if other is robot:
                    continue
                robot_circles.append(
                    np.array([other.x, other.y, float(other.radius)])
                )

        for angle in angles:
            ray_dir = np.array([math.cos(angle), math.sin(angle)])
            min_d = self.range
            hit = robot.position + ray_dir * self.range
            
            # 1. Cast against grid map if available
            if grid_map is not None:
                d, h = grid_map.cast_ray(robot.x, robot.y, angle, self.range)
                if d < min_d:
                    min_d = d
                    hit = h

            # 2. Cast against circular obstacles
            for obs in world.obstacles:
                d = self.ray_circle_intersection(robot.position, ray_dir, obs)
                if d is not None and d < min_d:
                    min_d = d
                    hit = robot.position + ray_dir * d

            # 3. Cast against the other robots (moving obstacles)
            for circle in robot_circles:
                d = self.ray_circle_intersection(robot.position, ray_dir, circle)
                if d is not None and d < min_d:
                    min_d = d
                    hit = robot.position + ray_dir * d
            readings.append((angle, min_d, hit))
        return readings

    # draw method removed - rendering is handled by frontend