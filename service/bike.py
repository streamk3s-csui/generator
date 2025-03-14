import json
import random
import uuid
import aiohttp
import asyncio
import requests

from datetime import datetime
from config.variables import (
    POD_IP,
    API_PORT,
    PUBLISH_PATH,
    POD_NAME,
    NAMESPACE,
    BURST_SIZE,
    BURST_RATE,
)
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
        self.gpxd = gpxd
        self.burst_size = BURST_SIZE  # Number of messages per burst
        self.λ_burst = BURST_RATE  # Bursts per second

    def _flatten_points(self):
        """Flatten all GPX track points into a single list."""
        points = []
        for track in self.gpxd.tracks:
            for segment in track.segments:
                points.extend(segment.points)
        return points

    async def start(self) -> None:
        """Start sending bursts of messages with Poisson-distributed inter-burst times."""
        self.active = True
        self.battery_level = random.randint(75, 100)

        async with aiohttp.ClientSession() as session:
            self._session = session
            point_index = 0
            while point_index < len(self.points):
                if not self.active:
                    return
                # Send a burst of messages
                burst_end = min(point_index + self.burst_size, len(self.points))
                for i in range(point_index, burst_end):
                    point = self.points[i]
                    await self.publish(point.latitude, point.longitude, point.elevation)
                    await asyncio.sleep(0.01)  # Small delay between messages

                point_index = burst_end
                # Wait for the next burst with exponential delay
                if point_index < len(self.points):
                    inter_burst_time = random.expovariate(self.λ_burst)
                    await asyncio.sleep(inter_burst_time)

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

    async def publish(self, lat: float, lon: float, elevation: float) -> None:
        """Send data asynchronously"""
        try:
            data = {
                "bike_id": str(self.id),
                "number": self.number,
                "timestamp": datetime.now().isoformat(),
                "location": {"latitude": lat, "longitude": lon, "elevation": elevation},
                "battery_level": self.battery_level,
                "temperature": random.uniform(20, 35),
                "speed": random.uniform(0, 25),
                "active": self.active,
            }

            async with self._session.post(
                f"http://{self.pod_ip}:{self.api_port}{self.publish_path}",
                data=json.dumps(data),
                headers={"Content-Type": "application/json"},
                timeout=5,
            ) as response:
                response.raise_for_status()
                logger.debug(f"Bike {self.number} published data")

        except Exception as e:
            logger.error(f"Bike {self.number} failed to publish: {str(e)}")
            self.active = False

    def get_speed(self) -> float:
        """
        Calculate speed from latitude,longitude diffs.
        """
        return 0.0
