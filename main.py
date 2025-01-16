import os
import random

from collections import defaultdict

import gpxpy
import gpxpy.gpx
import time
import multiprocessing
import pickle

from config.logging import logger
from config.utils import get_env_value, setup_env
from config.variables import LOAD_CONFIG
from service.bike import Bike
from service.load_pattern import LoadPattern, LoadConfig
from concurrent.futures import ThreadPoolExecutor


def start(bikes: dict[Bike]) -> None:
    """
    Manage bike activation/deactivation

    elif current < target:
    - Activate bikes
    elif current > target:
    - Too many bikes
    - Deactivate bikes
    """
    inactive, active = bikes, {}

    load_pattern = LoadPattern(
        LoadConfig(
            base_rate=LOAD_CONFIG["base_rate"],
            peak_rate=LOAD_CONFIG["peak_rate"],
            cycle_duration=LOAD_CONFIG["cycle_duration"],
        )
    )

    while True:
        try:
            target_rate = load_pattern.get_next_rate()
            target_bikes = int(target_rate / 2)
            current_bikes = len(active)

            logger.info(f"Current bikes: {current_bikes}, Target bikes: {target_bikes}")

            for bike in active.values():
                if bike.active:
                    bike.publish_current_state()

            # Handle bike count adjustments
            if current_bikes < target_bikes:
                to_activate = target_bikes - current_bikes
                for _ in range(to_activate):
                    if not inactive:
                        break
                    number, bike = inactive.popitem()
                    bike.start()
                    active[number] = bike
            elif current_bikes > target_bikes:
                to_deactivate = current_bikes - target_bikes
                for _ in range(to_deactivate):
                    if not active:
                        break
                    number, bike = active.popitem()
                    bike.finish()
                    inactive[number] = bike

            logger.info(f"Rate: {target_rate} msg/s, Active Publishing Bikes: {len([b for b in active.values() if b.active])}")
            time.sleep(1)

        except Exception as e:
            logger.error(f"Load management error: {str(e)}")
            time.sleep(1)


def load_gpx_file(file_path: str) -> gpxpy.gpx.GPX:
    cache_path = f"{file_path}.cache"
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as cache_file:
            return pickle.load(cache_file)

    with open(file_path, "r", encoding="utf-8") as f:
        gpxd = gpxpy.parse(f)

        with open(cache_path, "wb") as cache_file:
            pickle.dump(gpxd, cache_file)
        return gpxd


def parallel_load_gpx(file_paths: list) -> list:
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        return list(executor.map(load_gpx_file, file_paths))


def main() -> None:
    setup_env()
    N = 100  # Reduced for testing
    GPX_DATAPATH = get_env_value("GPX_DATAPATH")

    gpx_files = [
        os.path.join(GPX_DATAPATH, f)
        for f in os.listdir(GPX_DATAPATH)
        if f.endswith(".gpx")
    ]

    logger.info(f"Loading {len(gpx_files)} GPX files in parallel...")
    gpx_data = parallel_load_gpx(gpx_files)

    # Create bikes with loaded GPX data
    bikes = defaultdict(Bike)
    for i in range(N):
        bikes[i] = Bike(i, random.choice(gpx_data))

    start(bikes)


if __name__ == "__main__":
    main()
