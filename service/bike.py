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
    LAMBDA_BIKE,
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

    async def start(self) -> None:
        """Start bike journey asynchronously"""
        self.active = True
        self.battery_level = random.randint(75, 100)
        logger.info(f"Bike {self.number} started its track")
        async with aiohttp.ClientSession() as session:
            self._session = session
            for track in self.gpxd.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        if not self.active:
                            return
                        await self.publish(
                            point.latitude, point.longitude, point.elevation
                        )
                        # Add exponential delay to simulate poisson distribution
                        # Rather than using fixed sleep.
                        await asyncio.sleep(random.expovariate(LAMBDA_BIKE))
        self.finish()

    def finish(self):
        """Stop bike journey and send termination"""
        self.active = False
        termination_msg = {"pod": POD_NAME, "namespace": NAMESPACE, "status": "ended"}
        requests.post(
            f"http://{self.pod_ip}:{self.api_port}{self.publish_path}",
            json=termination_msg,
        )
        logger.info(
            f"Bike {self.number} finished its track and sent termination message."
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
