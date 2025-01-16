import os
import random
import time
import uuid

from datetime import datetime

import gpxpy
import gpxpy.gpx
import requests
from config.variables import POD_IP, API_PORT, PUBLISH_PATH, POD_NAME, NAMESPACE
from config.logging import logger


class Bike:
    def __init__(self, number: int, gpxd) -> None:
        self.id = uuid.uuid4()
        self.pod_ip = POD_IP
        self.api_port = API_PORT
        self.publish_path = PUBLISH_PATH
        self.number: int = number
        self.battery_level: int = 100
        self.temp: float = 30.0
        self.latitude: float = 0
        self.longitude: float = 0
        self.speed: float = 0
        self.active: bool = False
        self.gpxd = gpxd  # parsed gpx dataset

    def start(self) -> None:
        """Start bike journey along GPX track"""
        self.active = True
        self.battery_level = random.randint(75, 100)

        for track in self.gpxd.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if not self.active:
                        return
                    self.publish(point.latitude, point.longitude, point.elevation)
                    time.sleep(0.5)

        self.finish()

    def finish(self) -> None:
        """Stop bike journey and send termination"""
        self.active = False
        # Need to add termination message
        termination_msg = {"pod": POD_NAME, "namespace": NAMESPACE, "status": "ended"}
        # Send termination message
        requests.post(
            f"http://{self.pod_ip}:{self.api_port}{self.publish_path}",
            json=termination_msg,
        )

    def publish(self, latitude: float, longitude: float, elevation: float) -> None:
        """Send daata"""
        try:
            self.latitude = latitude
            self.longitude = longitude
            self.speed = random.uniform(0, 25)
            self.battery_level -= 0.01

            data = {
                "bike_id": str(self.id),
                "number": self.number,
                "timestamp": datetime.now().isoformat(),
                "location": {
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "elevation": elevation,
                },
                "battery_level": self.battery_level,
                "temperature": self.temp,
                "speed": self.speed,
                "active": self.active,
            }

            response = requests.post(
                f"http://{self.pod_ip}:{self.api_port}{self.publish_path}",
                json=data,
                timeout=5,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to publish data: {str(e)}")
            self.active = False  # Stop bike

    def get_speed(self) -> float:
        """
        Calculate speed from latitude,longitude diffs.
        """
        return 0.0
