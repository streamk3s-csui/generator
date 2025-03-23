import os
from dotenv import load_dotenv

load_dotenv()

# StreamK3s environment variables
POD_IP = os.getenv("MY_POD_IP")
API_PORT = os.getenv("API_PORT", "4321")
PUBLISH_PATH = os.getenv("PUBLISH_PATH")
POD_NAME = os.getenv("MY_POD_NAME")
NAMESPACE = os.getenv("MY_POD_NAMESPACE")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
GPX_DATAPATH = os.getenv("GPX_DATAPATH", "/dataset")

# Load pattern configuration
LOAD_CONFIG = {"base_rate": 100, "peak_rate": 1000, "cycle_duration": 300}

# Burst size (number of messages per burst)
BURST_SIZE = 50

# Burst rate (bursts per second)
BURST_RATE = 0.1  # 1 burst every 10 seconds
