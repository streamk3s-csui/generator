import math
import time
import numpy as np
from dataclasses import dataclass


@dataclass
class LoadConfig:
    base_rate: int
    peak_rate: int
    cycle_duration: int = 300
    transition_step: float = 0.5  # Max 10% change per step


class LoadPattern:
    def __init__(self, config: LoadConfig):
        self.config = config
        self.start_time = time.time()
        self.current_rate = config.base_rate

    def get_target_rate(self) -> int:
        elapsed = time.time() - self.start_time
        cycle_position = (
            elapsed % self.config.cycle_duration
        ) / self.config.cycle_duration

        rate_range = self.config.peak_rate - self.config.base_rate
        target = (
            self.config.base_rate
            + rate_range * (math.sin(cycle_position * 2 * math.pi) + 1) / 2
        )

        return int(np.random.poisson(target))

    def get_next_rate(self) -> int:
        target = self.get_target_rate()
        max_change = self.current_rate * self.config.transition_step

        if target > self.current_rate:
            self.current_rate = min(target, self.current_rate + max_change)
        else:
            self.current_rate = max(target, self.current_rate - max_change)

        return int(self.current_rate)
