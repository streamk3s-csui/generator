import os
import random

from collections import defaultdict

import gpxpy
import gpxpy.gpx
import asyncio
import multiprocessing
import pickle
import traceback

from config.logging import logger
from config.utils import get_env_value, setup_env
from config.variables import LOAD_CONFIG, BURST_RATE, BURST_SIZE
from service.bike import Bike
from service.load_pattern import LoadPattern, LoadConfig
from concurrent.futures import ThreadPoolExecutor


async def handle_task_exception(task: asyncio.Task) -> None:
    try:
        await task
    except Exception as e:
        logger.error(
            f"Unhandled exception in task {task.get_name()}: {str(e)}\n{traceback.format_exc()}"
        )


async def load_controller(gpx_data):
    load_pattern = LoadPattern(
        LoadConfig(base_rate=100, peak_rate=1000, cycle_duration=300)
    )

    average_rate_per_bike = BURST_SIZE * BURST_RATE  # e.g., 5 messages/second

    active_bikes = {}
    inactive_bikes = {}

    while True:
        target_rate = load_pattern.get_next_rate()

        # Calculate bikes needed
        target_bikes = max(1, int(target_rate / average_rate_per_bike))

        logger.info(f"Starting new batch: {target_bikes} bikes")

        # Start a batch of bikes
        for _ in range(target_bikes):
            if inactive_bikes:
                num, bike = inactive_bikes.popitem()
            else:
                num = len(active_bikes) + len(inactive_bikes)
                bike = Bike(
                    number=num,
                    gpxd=random.choice(gpx_data),
                )
            task = asyncio.create_task(bike.start(), name=f"bike-{num}")
            task.add_done_callback(handle_task_exception)
            active_bikes[num] = bike

        # Monitor active bikes until they finish
        while active_bikes:
            await asyncio.sleep(1)  # Check every second
            finished_bikes = {
                num: bike for num, bike in active_bikes.items() if not bike.active
            }
            for num, bike in finished_bikes.items():
                del active_bikes[num]
                inactive_bikes[num] = bike

        logger.info("All bikes in batch finished. Recalculating for next batch.")
        await asyncio.sleep(1)


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


async def main():
    """Main async entry point with error boundaries"""
    try:
        setup_env()
    except Exception as e:
        logger.critical(f"Failed to load environment: {str(e)}")
        return

    try:
        GPX_DATAPATH = get_env_value("GPX_DATAPATH")
    except Exception as e:
        logger.critical(f"Missing GPX_DATAPATH: {str(e)}")
        return

    try:
        gpx_files = [
            os.path.join(GPX_DATAPATH, f)
            for f in os.listdir(GPX_DATAPATH)
            if f.endswith(".gpx")
        ]
        logger.info(f"Found {len(gpx_files)} GPX files")

        # Load GPX data with error handling
        gpx_data = await asyncio.to_thread(parallel_load_gpx, gpx_files)
        if not gpx_data:
            logger.error("No valid GPX data loaded")
            return

        await load_controller(gpx_data)

    except Exception as e:
        logger.critical(f"Main execution failed: {str(e)}\n{traceback.format_exc()}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.critical(f"Catastrophic failure: {str(e)}\n{traceback.format_exc()}")
