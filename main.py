import os
import random

from collections import defaultdict

import gpxpy
import gpxpy.gpx

from config.logging import Logger
from config.utils import get_env_value, setup_env
from service.bike import Bike


logger = Logger().setup_logger('main_executor')


def start(bikes: dict[Bike]) -> None:
    """
    TODO
    """
    inactive, active = bikes, {}
    # throughput (active:inactive bike ratio)
    T = {
        'low' : [101 , 1000],
        'med' : [1001, 2500],
        'high': [2501, 5000]
    } 

    while True:
        throughput = T[list(T.keys())[random.randint(0, 2)]]
        lbound, hbound = throughput

        # if len(active) < lbound:
        #     for _ in range(random.randint(lbound + 1, hbound)):
        #         bike = inactive.popitem()
        #         bike.start()
        #         active[bike.number] = bike

        logger.info(f'{len(inactive)} inactive bikes - {len(active)} active bikes.')



def main() -> None:
    setup_env()

    N = 5000

    datasets = os.listdir(get_env_value('GPX_DATAPATH'))

    # create N bikes
    bikes = defaultdict(Bike)
    for i in range(N):
        # preload gpx data to cut resource usage on bike restart
        gpxf = datasets[random.randint(0, len(datasets) - 1)]
        gpxd = gpxpy.parse(gpxf)
        bikes[i] = Bike(i, gpxd)

    start(bikes)


if __name__ == '__main__':
    main()
