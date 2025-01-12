import os
import random
import time
import uuid

from datetime import datetime

import gpxpy
import gpxpy.gpx

from config.logging import Logger
# from mqtt.publish import 



class Bike:
    def __init__(self, number: int, datapath: str) -> None:
        self.id = uuid.uuid4()
        self.number: int = number
        self.battery_level: int = 100
        self.temp: float = 30.0
        self.latitude: float = 0
        self.longitude: float = 0
        self.speed: float = 0 
        self.active: bool = False
        self.datapath: str = datapath   # path to gpx dataset
        self.logger: Logger = Logger().setup_logger(f'bike_{number}')
    

    def start(self) -> None:
        """
        Selects and parses a random `.gpx` path dataset, then traces it to simulate realtime bike activity.
        Sends trace data to MQTT broker with a delay of `latency`, defaults to 0.5 seconds.
        """
        datasets = os.listdir(self.datapath)
        data = datasets[random.randint(0, len(datasets) - 1)]
        
        self.active = True
        self.battery_level = random.randint(75, 100)
        with open(f'{self.datapath}/{data}', 'r') as gpxf:
            gpx = gpxpy.parse(gpxf) 
            
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        self.logger.info(f'[TRACK] Point at ({point.latitude},{point.longitude}) -> {point.elevation}')
                        self.publish(point.latitude, point.longitude, point.elevation)
            
            for waypoint in gpx.waypoints:
                self.logger.info(f'[WAYPOINT] Waypoint {waypoint.name} -> ({waypoint.latitude},{waypoint.longitude})')
                 
            for route in gpx.routes:
                self.logger.info('[ROUTE] Route: ')
                for point in route.points:
                    self.logger.info(f'[ROUTE] Point at ({point.latitude},{point.longitude}) -> {point.elevation}')


    def finish(self) -> None:
        raise NotImplementedError
    

    def publish(self, latitude: float, longitude: float, elevation: float) -> None:
        """
        Publish a single trace data point to MQTT broker with simulated latency.
        """
        # probability distribution k:v
        # k = latency, v = probability
        dist = {
            0.1     : 0.3,
            0.25    : 0.1,
            0.5     : 0.2,
            0.75    : 0.1, 
            1       : 0.3 
        }
        latency = random.choice(list(dist.keys()), list(dist.values()))
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

    

    def get_speed(self) -> float:
        """
        Calculate speed from latitude,longitude diffs.
        """
        raise NotImplementedError
    
