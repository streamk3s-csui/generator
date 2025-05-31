import os
import random
import time
import threading
from locust import HttpUser, task, events
from locust.runners import MasterRunner, LocalRunner
import gpxpy
import pickle
from concurrent.futures import ThreadPoolExecutor
from config.variables import GPX_DATAPATH, LAMBDA_BIKE, PUBLISH_PATH
from config.logging import logger
from service.load_pattern import LoadPattern, LoadConfig
from datetime import datetime
import uuid

gpx_data = []


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


def manage_bike_load(environment):
    load_pattern = LoadPattern(
        LoadConfig(base_rate=20, peak_rate=80, cycle_duration=300)
    )
    while True:
        target_rate = load_pattern.get_next_rate()
        target_bikes = max(1, int(target_rate / LAMBDA_BIKE))
        environment.runner.start(user_count=target_bikes, spawn_rate=10, wait=False)
        time.sleep(1)


@events.test_start.add_listener
def on_test_start_manage_bikes(environment, **kwargs):
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        thread = threading.Thread(target=manage_bike_load, args=(environment,))
        thread.daemon = True
        thread.start()


class BikeUser(HttpUser):
    def on_start(self):
        self.track = random.choice(gpx_data)
        self.points = self._flatten_points()
        self.point_index = 0
        self.number = random.randint(1, 10000)
        self.id = str(uuid.uuid4())

    def _flatten_points(self):
        points = []
        for track in self.track.tracks:
            for segment in track.segments:
                points.extend(segment.points)
        return points

    @task
    def send_messages(self):
        while True:
            if self.point_index >= len(self.points):
                self.point_index = 0
            point = self.points[self.point_index]
            self.publish(point.latitude, point.longitude, point.elevation)
            self.point_index += 1
            time.sleep(random.expovariate(LAMBDA_BIKE))

    def publish(self, lat, lon, elevation):
        data = {
            "bike_id": self.id,
            "number": self.number,
            "timestamp": datetime.now().isoformat(),
            "location": {"latitude": lat, "longitude": lon, "elevation": elevation},
            "battery_level": random.randint(75, 100),
            "temperature": random.uniform(20, 35),
            "speed": random.uniform(0, 25),
            "active": True,
        }
        self.client.post(PUBLISH_PATH, json=data)

    def on_stop(self):
        logger.info(f"Bike {self.number} stopped")
