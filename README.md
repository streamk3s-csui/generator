# Bike Sharing Streaming Dataset - Prototype

Currently written in Python for faster iteration and prototyping. Uses MQTT protocol with `paho-mqtt` package to simulate IoT datastream.

Simulates bike sharing data streams by first generating N number of bike data, then randomly selecting which one will be active with the following constraints:

1. At a time, there will be a minimum of `10 < N` number of bikes active.
2. There will be fluctuations where the number of bikes active will be in the following range:
   1. Low throughput simulation: `100 < N < 500`
   2. Medium throughput simulation: `500 < N < 1000`
   3. High throughput simulation: `1000 < N < 1500`

Data generated from those bikes will then be sent to an external message broker running on the StreamK3s platform, hosting a MQTT message broker as its operator image.

## Dataset

Dataset sourced from [OpenStreetMap](https://www.openstreetmap.org/traces)'s public traces and [GPX Studio](https://gpx.studio/), where a route of UI campus outer ring was dumped into a `.gpx` file.

The `.gpx` file will then be parsed with the [gpxpy](https://pypi.org/project/gpxpy/) package on each bike to simulate them going through the routes from its start to its waypoint, resulting in realistic latitude & longitude data. Time will be the same as host time, and speed & temperatures will be randomized. Battery levels will drain with a fixed rate where only the start level will be randomized.

## Quickstart (development)

1. Setup virtual environment:

   Windows

   ```
   python -m venv .venv
   .venv\Scripts\activate.bat
   ```

   Linux

   ```
   virtualenv .venv
   source .venv/bin/activate
   ```

2. Install required packages:

   ```
   pip install -r requirements.txt
   ```

3. Setup `.env` file from `.env.example`

4. Run with:

   ```
   python main.py
   ```

How to run the locust?

```
locust -f locustfile.py --host=http://localhost:4321 --headless --users 0 --run-time 1m
```

Docker config on development after scenario are finished
