from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np


class BaseRobot(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.path = []

    @property
    @abstractmethod
    def position(self) -> np.ndarray:
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def state(self) -> dict:
        pass

    @abstractmethod
    def step(self, command: dict, dt: float):
        pass

    @abstractmethod
    def draw(self, screen, camera):
        pass

    def clear_path(self):
        self.path.clear()
