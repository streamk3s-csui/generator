import time
import uuid

from config.logging import Logger


class Bike:
    def __init__(self, number: int, battery_level: int, datapath: str) -> None:
        self.id = uuid.uuid4()
        self.number: int = number
        self.battery_level: int = battery_level
        self.temp: float = 30.0
        self.latitude: float = 0
        self.longitude: float = 0
        self.speed: float = 0 
        self.active: bool = False
        self.datapath: str = datapath   # path to gpx dataset
        self.logger: Logger = Logger().setup_logger(f'bike_{number}')
    

    def start(self) -> None:
        raise NotImplementedError
    
    def finish(self) -> None:
        raise NotImplementedError
    
    