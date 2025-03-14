import os
import random

import gpxpy
import gpxpy.gpx
import asyncio
import multiprocessing
import pickle
import traceback

from config.logging import logger
from config.utils import get_env_value, setup_env
from config.variables import LOAD_CONFIG, LAMBDA_BIKE
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


async def manage_load(
    active_bikes: dict, inactive_bikes: dict, target_bikes: int, gpx_data: list
):
    """Dynamically scale bikes based on rate"""
    try:
        current_bikes = len(active_bikes)

        if current_bikes < target_bikes:
            needed = target_bikes - current_bikes
            for _ in range(needed):
                try:
                    if not inactive_bikes:
                        # Create new bike if pool is empty
                        new_bike = Bike(
                            number=len(active_bikes) + len(inactive_bikes),
                            gpxd=random.choice(gpx_data),
                        )
                        inactive_bikes[new_bike.number] = new_bike
                        logger.debug(f"Created new bike {new_bike.number}")

                    num, bike = inactive_bikes.popitem()
                    task = asyncio.create_task(bike.start(), name=f"bike-{num}")
                    task.add_done_callback(handle_task_exception)
                    active_bikes[num] = bike
                except Exception as e:
                    logger.error(
                        f"Failed to activate bike: {str(e)}\n{traceback.format_exc()}"
                    )

        elif current_bikes > target_bikes:
            excess = current_bikes - target_bikes
            for _ in range(excess):
                try:
                    if active_bikes:
                        num, bike = active_bikes.popitem()
                        bike.active = False  # Signal to stop
                        inactive_bikes[num] = bike
                        logger.debug(f"Deactivated bike {num}")
                except Exception as e:
                    logger.error(
                        f"Failed to deactivate bike: {str(e)}\n{traceback.format_exc()}"
                    )

    except Exception as e:
        logger.error(
            f"Critical error in load management: {str(e)}\n{traceback.format_exc()}"
        )
        raise


async def load_controller(gpx_data: list):
    """Main control loop with error recovery"""
    load_config = LoadConfig(
        base_rate=LOAD_CONFIG["base_rate"],
        peak_rate=LOAD_CONFIG["peak_rate"],
        cycle_duration=LOAD_CONFIG["cycle_duration"],
    )
    load_pattern = LoadPattern(load_config)
    active_bikes = {}
    inactive_bikes = {}

    while True:
        try:
            target_rate = load_pattern.get_next_rate()
            target_bikes = max(10, int(target_rate / LAMBDA_BIKE))

            await manage_load(active_bikes, inactive_bikes, target_bikes, gpx_data)

            logger.info(
                f"Target: {target_rate} msg/s | "
                f"Target Bikes: {target_bikes} | "
                f"Active Bikes: {len(active_bikes)} | "
                f"Inactive Pool: {len(inactive_bikes)}"
            )
            await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            for bike in active_bikes.values():
                bike.active = False
            raise

        except Exception as e:
            logger.error(
                f"Fatal error in controller loop: {str(e)}\n{traceback.format_exc()}"
            )
            await asyncio.sleep(5)  # Prevent tight error loops


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
