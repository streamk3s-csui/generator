# Bike Sharing Streaming Dataset - Prototype

Currently written in Python for faster iteration and prototyping. Uses MQTT protocol with `paho-mqtt` package to simulate IoT datastream.

Simulates bike sharing data streams by first generating N number of bike data, then randomly selecting which one will be active with the following constraints:

1. At a time, there will be a minimum of `10 < N` number of bikes active.
2. There will be fluctuations where the number of bikes active will be in the following range:
   1. Low throughput simulation: `10 < N < 100`
   2. Medium throughput simulation: `100 < N < 1000`
   3. High throughput simulation: `1000 < N`
   
Data generated from those bikes will then be sent to an external message broker running on the StreamK3s platform, hosting a MQTT message broker as its operator image.