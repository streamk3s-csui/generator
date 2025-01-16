import math
import random
import time
from dataclasses import dataclass


@dataclass
class LoadConfig:
    base_rate: int = 100  # Minimum messages/sec
    peak_rate: int = 1000  # Maximum messages/sec
    cycle_duration: int = 300  # Seconds for one complete wave
    transition_step: float = 0.1  # Max 10% change per step


class LoadPattern:
    def __init__(self, config: LoadConfig = LoadConfig()):
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

        # Add small random variation (±5%)
        noise = random.uniform(-0.05, 0.05) * target
        return int(target + noise)

    def get_next_rate(self) -> int:
        target = self.get_target_rate()
        max_change = self.current_rate * self.config.transition_step

        if target > self.current_rate:
            self.current_rate = min(target, self.current_rate + max_change)
        else:
            self.current_rate = max(target, self.current_rate - max_change)

        return int(self.current_rate)
