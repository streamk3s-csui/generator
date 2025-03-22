import random
import time
import uuid
from datetime import datetime

from config.logging import logger
from config.variables import LAMBDA_BIKE, POD_NAME, NAMESPACE


class Bike:
    def __init__(self, number: int, gpxd):
        self.id = str(uuid.uuid4())
        self.number = number
        self.gpxd = gpxd
        self.active = False
        self.battery_level = random.randint(75, 100)

    def run_track(self, client):
        """Run the bike’s track synchronously for Locust."""
        if not self.active:
            return
        logger.info(f"Bike {self.number} starting to run track")
        for track in self.gpxd.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if not self.active:
                        return
                    self.publish(
                        point.latitude, point.longitude, point.elevation, client
                    )
                    time.sleep(random.expovariate(LAMBDA_BIKE))
        self.finish(client)

    def publish(self, lat, lon, elevation, client):
        """Send data to the API."""
        data = {
            "bike_id": self.id,
            "number": self.number,
            "timestamp": datetime.now().isoformat(),
            "location": {"latitude": lat, "longitude": lon, "elevation": elevation},
            "battery_level": self.battery_level,
            "temperature": random.uniform(20, 35),
            "speed": random.uniform(0, 25),
            "active": self.active,
        }
        try:
            response = client.post("/post_message", json=data)
            if response.status_code != 200:
                logger.error(f"Bike {self.number} failed to publish: {response.text}")
        except Exception as e:
            logger.error(f"Bike {self.number} failed to publish: {str(e)}")

    def finish(self, client):
        """Deactivate and send termination message."""
        self.active = False
        termination_msg = {
            "pod": POD_NAME,
            "namespace": NAMESPACE,
            "status": "ended",
        }
        client.post("/post_message", json=termination_msg)
        logger.info(
            f"Bike {self.number} finished its track and sent termination message."
        )
