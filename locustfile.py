import os
import random
import uuid
import time
from datetime import datetime
from locust import HttpUser, task, events
from locust.exception import StopUser
from locust.runners import MasterRunner, LocalRunner
import gpxpy
import pickle
from concurrent.futures import ThreadPoolExecutor
from config.variables import GPX_DATAPATH, LAMBDA_BIKE
from config.logging import logger
from service.load_pattern import LoadPattern, LoadConfig
import threading

# Constants
load_pattern = LoadPattern(
    LoadConfig(base_rate=100, peak_rate=1000, cycle_duration=300)
)
# Global variables
gpx_data = []
current_batch_id = 0
active_bike_count = 0  # Tracks active bikes in the current batch
batch_lock = threading.Lock()  # For thread-safe counter updates


# Load a single GPX file with caching
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


# Load all GPX files from a directory
def load_all_gpx(directory):
    gpx_files = [
        os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".gpx")
    ]
    if not gpx_files:
        raise Exception(f"No GPX files found in {directory}")
    with ThreadPoolExecutor() as executor:
        gpx_data = list(executor.map(load_gpx_file, gpx_files))
    return gpx_data


# Load GPX data when the test starts
@events.test_start.add_listener
def on_test_start_load_gpx(**kwargs):
    global gpx_data
    try:
        gpx_data = load_all_gpx(GPX_DATAPATH)
        logger.info(f"Loaded {len(gpx_data)} GPX files")
    except Exception as e:
        logger.error(f"Failed to load GPX files: {str(e)}")
        raise


# Batch management
def manage_batches(environment):
    global current_batch_id, active_bike_count
    while True:
        target_rate = load_pattern.get_next_rate()
        target_bikes = max(1, int(target_rate / LAMBDA_BIKE))
        logger.info(
            f"Starting batch {current_batch_id} with {target_bikes} bikes (λ_total={target_rate})"
        )

        with batch_lock:
            active_bike_count = target_bikes
        environment.runner.start(user_count=target_bikes, spawn_rate=1, wait=False)

        while True:
            with batch_lock:
                if active_bike_count <= 0:
                    break
            time.sleep(1)

        environment.runner.stop()
        logger.info(f"Batch {current_batch_id} completed")
        current_batch_id += 1


# BikeUser class
class BikeUser(HttpUser):
    host = "http://localhost:4321"

    def on_start(self):
        self.track = random.choice(gpx_data)
        self.number = random.randint(1, 10000)
        self.id = str(uuid.uuid4())
        self.batch_id = current_batch_id
        logger.info(f"Bike {self.number} (batch {self.batch_id}) started")

    @task
    def run_track(self):
        logger.info(f"Bike {self.number} (batch {self.batch_id}) starting to run track")
        for track in self.track.tracks:
            for segment in track.segments:
                for point in segment.points:
                    self.publish(point.latitude, point.longitude, point.elevation)
                    time.sleep(random.expovariate(LAMBDA_BIKE))

        # Send termination message
        termination_msg = {
            "pod": f"bike-{self.number}",
            "namespace": "test",
            "status": "ended",
        }
        self.client.post("/post_message", json=termination_msg)
        logger.info(f"Bike {self.number} (batch {self.batch_id}) finished track")

        # Decrement active bike count
        global active_bike_count
        with batch_lock:
            active_bike_count -= 1
        raise StopUser()

    def publish(self, lat, lon, elevation):
        data = {
            "bike_id": self.id,
            "number": self.number,
            "timestamp": datetime.now().isoformat(),
            "location": {"latitude": lat, "longitude": lon, "elevation": elevation},
            "battery_level": random.randint(0, 100),
            "temperature": random.uniform(20, 35),
            "speed": random.uniform(0, 25),
            "active": True,
        }
        response = self.client.post("/post_message", json=data)
        if response.status_code != 200:
            logger.error(f"Bike {self.number} failed to publish: {response.text}")


# Start the batch manager
@events.test_start.add_listener
def on_test_start_manage_batches(environment, **kwargs):
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        environment.runner.greenlet.spawn(manage_batches, environment)
