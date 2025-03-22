import os
import random
import time
from locust import HttpUser, task, events
from locust.exception import StopUser
from locust.runners import MasterRunner, LocalRunner
import gpxpy
import pickle
from concurrent.futures import ThreadPoolExecutor
from config.variables import GPX_DATAPATH, LAMBDA_BIKE
from config.logging import logger
from service.load_pattern import LoadPattern, LoadConfig
from service.locust_bike import Bike
import threading

gpx_data = []
active_bikes = {}  # Active bike instance
inactive_bikes = {}  # Inactive bike instance
bike_lock = threading.Lock()  # Thread-safe access to bike pools


# Load GPX files
def load_gpx_file(file_path):
    cache_path = f"{file_path}.cache"
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as cache_file:
            return pickle.load(cache_file)
    with open(file_path, "r", encoding="utf-8") as f:
        gpxd = gpxpy.parse(f)
        with open(cache_path, "wb") as cache_file:
            pickle.dump(gpxd, cache_file)
        return gpxd


def load_all_gpx(directory):
    gpx_files = [
        os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".gpx")
    ]
    if not gpx_files:
        raise Exception(f"No GPX files found in {directory}")
    with ThreadPoolExecutor() as executor:
        return list(executor.map(load_gpx_file, gpx_files))


@events.test_start.add_listener
def on_test_start_load_gpx(**kwargs):
    global gpx_data
    try:
        gpx_data = load_all_gpx(GPX_DATAPATH)
        logger.info(f"Loaded {len(gpx_data)} GPX files")
    except Exception as e:
        logger.error(f"Failed to load GPX files: {str(e)}")
        raise


# Manage bike activation/deactivation
def manage_bike_load(environment):
    load_pattern = LoadPattern(
        LoadConfig(base_rate=100, peak_rate=1000, cycle_duration=300)
    )
    while True:
        target_rate = load_pattern.get_next_rate()
        target_bikes = max(10, int(target_rate / LAMBDA_BIKE))
        current_bikes = len(active_bikes)

        with bike_lock:
            if current_bikes < target_bikes:
                needed = target_bikes - current_bikes
                for _ in range(needed):
                    if inactive_bikes:
                        num, bike = inactive_bikes.popitem()
                        bike.active = True
                        active_bikes[num] = bike
                        logger.info(f"Reactivated bike {num}")
                    else:
                        new_bike = Bike(
                            number=len(active_bikes) + len(inactive_bikes),
                            gpxd=random.choice(gpx_data),
                        )
                        new_bike.active = True
                        active_bikes[new_bike.number] = new_bike
                        logger.info(f"Created and activated bike {new_bike.number}")

            elif current_bikes > target_bikes:
                excess = current_bikes - target_bikes
                for _ in range(excess):
                    if active_bikes:
                        num, bike = active_bikes.popitem()
                        bike.active = False
                        inactive_bikes[num] = bike
                        logger.info(f"Deactivated bike {num}")

            # User Adjustment
            current_users = environment.runner.user_count
            if current_users < target_bikes:
                environment.runner.start(
                    user_count=target_bikes, spawn_rate=10, wait=False
                )
            elif current_users > target_bikes:
                environment.runner.stop_users(count=current_users - target_bikes)

        logger.info(
            f"Target: {target_rate} msg/s | Target Bikes: {target_bikes} | "
            f"Active Bikes: {len(active_bikes)} | Inactive Pool: {len(inactive_bikes)}"
        )
        time.sleep(1)


@events.test_start.add_listener
def on_test_start_manage_bikes(environment, **kwargs):
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        environment.runner.greenlet.spawn(manage_bike_load, environment)


class BikeUser(HttpUser):
    def on_start(self):
        with bike_lock:
            if not active_bikes:
                time.sleep(1)
                if not active_bikes:
                    raise StopUser("No active bikes available")
            # Pop a bike from active_bikes so that we know
            # who is assigned to this bikeuser right now
            # and this will also prevent the same bike
            # from being assigned to multiple users
            num, self.bike = active_bikes.popitem()
            self.bike.active = True  # Make sure active
        logger.info(f"User assigned to bike {self.bike.number}")

    @task
    def run_track(self):
        if self.bike.active:
            self.bike.run_track(self.client)
            with bike_lock:
                # Because previously it was popped from active_bikes
                # now we need to add it back to inactive_bikes
                # se;f.bike.active = False will be handled when track is finished
                if self.bike.number not in active_bikes:
                    inactive_bikes[self.bike.number] = self.bike
                    logger.info(f"Bike {self.bike.number} moved to inactive pool")
        raise StopUser()
