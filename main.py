from config.logging import Logger
from config.utils import get_env_value, setup_env
from models.bike import Bike



if __name__ == '__main__':

    setup_env()

    logger = Logger().setup_logger('main_executor')

    logger.info(get_env_value('GPX_DATAPATH'))

    logger.info(get_env_value('MQTT_BROKER_ADDR'))    
    logger.info(get_env_value('MQTT_BROKER_TOPIC'))    

    logger.info(get_env_value('VECTOR_SINK_ADDR'))

    bike = Bike(1, 100, get_env_value('GPX_DATAPATH'))    

