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
from config.variables import (
    GPX_DATAPATH,
    BURST_SIZE,
    BURST_RATE,
    PUBLISH_PATH,
    POD_NAME,
    NAMESPACE,
)
from config.logging import logger
from service.load_pattern import LoadPattern, LoadConfig
import threading

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
        return list(executor.map(load_gpx_file, gpx_files))


# Load GPX data at test start
@events.test_start.add_listener
def on_test_start_load_gpx(**kwargs):
    global gpx_data
    try:
        gpx_data = load_all_gpx(GPX_DATAPATH)
        logger.info(f"Loaded {len(gpx_data)} GPX files")
    except Exception as e:
        logger.error(f"Failed to load GPX files: {str(e)}")
        raise


def manage_batches(environment):
    global current_batch_id, active_bike_count
    load_pattern = LoadPattern(
        LoadConfig(base_rate=100, peak_rate=1000, cycle_duration=300)
    )
    average_rate_per_bike = BURST_SIZE * BURST_RATE  # Messages per second per bike
    while True:
        target_rate = load_pattern.get_next_rate()
        target_bikes = max(1, int(target_rate / average_rate_per_bike))
        logger.info(
            f"Starting batch {current_batch_id} with {target_bikes} bikes (λ_total={target_rate})"
        )

        with batch_lock:
            active_bike_count = target_bikes
        environment.runner.start(user_count=target_bikes, spawn_rate=10, wait=False)

        while True:
            with batch_lock:
                if active_bike_count <= 0:
                    break
            time.sleep(1)

        environment.runner.stop()
        logger.info(f"Batch {current_batch_id} completed")
        current_batch_id += 1


# Start batch manager at test start
@events.test_start.add_listener
def on_test_start_manage_batches(environment, **kwargs):
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        environment.runner.greenlet.spawn(manage_batches, environment)


class BikeUser(HttpUser):
    def on_start(self):
        """Initialize bike with a random GPX track and settings."""
        self.track = random.choice(gpx_data)
        self.points = self._flatten_points()
        self.point_index = 0
        self.burst_size = BURST_SIZE  # Number of messages per burst
        self.λ_burst = BURST_RATE  # Bursts per second (Poisson rate)
        self.number = random.randint(1, 10000)
        self.id = str(uuid.uuid4())
        self.batch_id = current_batch_id
        logger.info(f"Bike {self.number} (batch {self.batch_id}) started")

    def _flatten_points(self):
        """Flatten GPX track points into a single list."""
        points = []
        for track in self.track.tracks:
            for segment in track.segments:
                points.extend(segment.points)
        return points

    @task
    def send_bursts(self):
        """Send bursts of messages with Poisson-distributed inter-burst times."""
        while self.point_index < len(self.points):
            # Send a burst of messages
            burst_end = min(self.point_index + self.burst_size, len(self.points))

            for i in range(self.point_index, burst_end):
                point = self.points[i]
                self.publish(point.latitude, point.longitude, point.elevation)
                time.sleep(0.01)  # Small delay between messages within burst
            self.point_index = burst_end

            # Wait for the next burst with exponential delay
            if self.point_index < len(self.points):
                inter_burst_time = random.expovariate(self.λ_burst)
                time.sleep(inter_burst_time)

        termination_msg = {
            "pod": POD_NAME,
            "namespace": NAMESPACE,
            "status": "ended",
        }
        self.client.post(PUBLISH_PATH, json=termination_msg)
        logger.info(f"Bike {self.number} (batch {self.batch_id}) finished track")

        global active_bike_count
        with batch_lock:
            active_bike_count -= 1
        raise StopUser()

    def publish(self, lat, lon, elevation):
        """Send a single message to the API endpoint."""
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
