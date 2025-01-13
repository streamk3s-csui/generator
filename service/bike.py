import os
import random
import time
import uuid

from datetime import datetime

import gpxpy
import gpxpy.gpx

from config.logging import Logger



class Bike:
    def __init__(self, number: int, gpxd) -> None:
        self.id = uuid.uuid4()
        self.number: int = number
        self.battery_level: int = 100
        self.temp: float = 30.0
        self.latitude: float = 0
        self.longitude: float = 0
        self.speed: float = 0 
        self.active: bool = False
        self.gpxd = gpxd    # parsed gpx dataset
    

    def start(self) -> None:
        """
        Selects and parses a random `.gpx` path dataset, then traces it to simulate realtime bike activity.
        Sends trace data to MQTT broker with a delay of `latency`, defaults to 0.5 seconds.
        """
        self.active = True
        self.battery_level = random.randint(75, 100)
            
        # for track in gpx.tracks:
        #     for segment in track.segments:
        #         for point in segment.points:
        #             # self.logger.info(f'[TRACK] Point at ({point.latitude},{point.longitude}) -> {point.elevation}')
        #             self.publish(point.latitude, point.longitude, point.elevation)

        self.finish()   

    def finish(self) -> None:
        raise NotImplementedError
    

    def publish(self, latitude: float, longitude: float, elevation: float) -> None:
        """
        Publish a single trace data point to MQTT broker with simulated latency.
        """
        # simulate latency between 0.1 and 0.5 secs with equal probability
        latency = random.choice([0.1, 0.2, 0.3, 0.4, 0.5], [0.2 for _ in range(5)])
        message = {
            "bike_id": str(self.id),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "loc": {
                "latitude": latitude,
                "longitude": longitude,
                "elevation": elevation, 
            },
            "status": {
                "speed": self.get_speed(),
                "battery_level": self.battery_level,
                "temperature": self.temp
            }
        }
        time.sleep(latency)
        # publish to mqtt

    

    def get_speed(self) -> float:
        """
        Calculate speed from latitude,longitude diffs.
        """
        raise NotImplementedError
    
